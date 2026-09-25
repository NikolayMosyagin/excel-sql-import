import pandas as pd
from mssql_python import Connection, Cursor

from src.sql_utils import quote_identifier
from src.import_config import ImportConfig, ImportMode
from src.import_result import ImportResult


TEMP_TABLE = "#ImportData"

def normalize_row(row: tuple) -> tuple:
    return tuple(None if pd.isna(value) else value for value in row)

def build_key_match_condition(key_columns: tuple[str, ...]) -> str:
    return " AND ".join(
        f"source.{quote_identifier(key)} = target.{quote_identifier(key)}" 
        for key in key_columns
    )


def insert_dataframe(
    cursor: Cursor,
    target_table: str,
    df: pd.DataFrame,
    column_names: list[str]
) -> int:
    df = df[column_names]
    rows = df.shape[0]
    batch_size = 1000
    insert_query = f"""INSERT INTO {target_table}
({', '.join(quote_identifier(name) for name in column_names)})
VALUES({', '.join('?' for _ in range(len(column_names)))})"""
    index = 0
    inserted_rows = 0
    while index < rows:
        values = [
            normalize_row(row) 
            for row in df.iloc[index:index+batch_size].itertuples(index=False, name=None)
        ]
        cursor.executemany(insert_query, values)
        inserted_rows += cursor.rowcount
        index += batch_size
    return inserted_rows


def write_dataframe(
    conn: Connection, 
    df: pd.DataFrame,
    column_names: list[str],
    import_config: ImportConfig
) -> ImportResult:
    target_table = (
            f"{quote_identifier(import_config.schema)}."
            f"{quote_identifier(import_config.table)}"
    )
    deleted_rows = 0
    with conn.cursor() as cursor:
        if import_config.mode == ImportMode.REPLACE:
            cursor.execute(f"DELETE FROM {target_table}")
            deleted_rows = cursor.rowcount
        inserted_rows = insert_dataframe(cursor, target_table, df, column_names)
    return ImportResult(
        inserted=inserted_rows,
        deleted=deleted_rows
    )


def create_temp_table(
    cursor: Cursor,
    column_names: list[str],
    target_table: str
)-> None:
    sql_query = f"""SELECT TOP (0)
{", ".join(quote_identifier(column_name) for column_name in column_names)}
INTO {TEMP_TABLE}
FROM {target_table}"""
    cursor.execute(sql_query)


def validate_upsert_matches(
    cursor: Cursor,
    import_config: ImportConfig,
    target_table: str
)-> None:
    key_columns_text = ", ".join(
        f"source.{quote_identifier(key)}" 
        for key in import_config.key_columns
    )
    sql_query = f"""SELECT TOP (1)
    {key_columns_text},
    COUNT(*)
FROM {TEMP_TABLE} AS source
JOIN {target_table} AS target ON 
    {build_key_match_condition(import_config.key_columns)}
GROUP BY
    {key_columns_text}
HAVING 
    COUNT(*) > 1"""
    cursor.execute(sql_query)
    row_data = cursor.fetchone()
    if row_data is not None:
        key_values = ", ".join(
            f"{column}={value}"
            for column, value in zip(import_config.key_columns, row_data[:-1], strict=True)
        )
        raise ValueError(
            f"Import '{import_config.name}':\n"
            f"UPSERT key ({key_values}) matches {row_data[-1]} rows "
            f"in target table '{import_config.schema}.{import_config.table}'. "
            f"Each UPSERT key must match at most one target row."
        )


def update_existing_rows(
    cursor: Cursor,
    column_names: list[str],
    key_columns: tuple[str, ...],
    target_table: str
) -> int:
    non_key_columns = [
        column
        for column in column_names
        if column not in key_columns
    ]
    if not non_key_columns:
        return 0

    sql_query = f"""UPDATE target
SET
    {", ".join(
        f"target.{quote_identifier(non_key)} = source.{quote_identifier(non_key)}" 
        for non_key in non_key_columns
    )}
FROM {target_table} AS target
JOIN {TEMP_TABLE} AS source ON
    {build_key_match_condition(key_columns)}"""
    
    cursor.execute(sql_query)
    return cursor.rowcount


def insert_missing_rows(
    cursor: Cursor,
    column_names: list[str],
    key_columns: tuple[str, ...],
    target_table: str,
)-> int:
    sql_query = f"""INSERT INTO {target_table}(
    {", ".join(quote_identifier(column) for column in column_names)}
)
SELECT 
    {", ".join(f"source.{quote_identifier(column)}" for column in column_names)}
FROM {TEMP_TABLE} AS source
WHERE NOT EXISTS(
    SELECT 1
    FROM {target_table} AS target
    WHERE {build_key_match_condition(key_columns)}
)"""
    cursor.execute(sql_query)
    return cursor.rowcount


def upsert_dataframe(
    conn: Connection,
    df: pd.DataFrame,
    column_names: list[str],
    import_config: ImportConfig
) -> ImportResult:

    target_table = (
        f"{quote_identifier(import_config.schema)}."
        f"{quote_identifier(import_config.table)}"
    )

    with conn.cursor() as cursor:
        create_temp_table(cursor, column_names, target_table)
        insert_dataframe(cursor, TEMP_TABLE, df, column_names)

        validate_upsert_matches(cursor, import_config, target_table)
        updated_rows = update_existing_rows(cursor, column_names, import_config.key_columns, target_table)

        inserted_rows = insert_missing_rows(cursor, column_names, import_config.key_columns, target_table)
        cursor.execute(f"DROP TABLE {TEMP_TABLE}")
    return ImportResult(
        inserted=inserted_rows,
        updated=updated_rows
    )

def delete_rows_by_columns(
    cursor: Cursor,
    df: pd.DataFrame,
    replace_columns: tuple[str, ...],
    target_table: str,
) -> int:

    delete_query = f"""DELETE FROM {target_table}
WHERE {" AND ".join(
    f"{quote_identifier(column)} = ?"
    for column in replace_columns
)}"""

    replace_values = df[list(replace_columns)].drop_duplicates()
    values = [
        normalize_row(row)
        for row in replace_values.itertuples(index=False, name=None)
    ]

    cursor.executemany(delete_query, values)
    return cursor.rowcount


def replace_by_columns_dataframe(
    conn: Connection,
    df: pd.DataFrame,
    column_names: list[str], 
    import_config: ImportConfig
) -> ImportResult:

    target_table = (
        f"{quote_identifier(import_config.schema)}."
        f"{quote_identifier(import_config.table)}"
    )

    with conn.cursor() as cursor:
        deleted_rows = delete_rows_by_columns(
            cursor,
            df,
            import_config.replace_columns,
            target_table
        )
        inserted_rows = insert_dataframe(cursor, target_table, df, column_names)
    return ImportResult(
        inserted=inserted_rows,
        deleted=deleted_rows
    )