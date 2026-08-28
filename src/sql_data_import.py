import pandas as pd
from mssql_python import Connection, Cursor

from src.sql_utils import quote_identifier
from src.import_config import ImportConfig, ImportMode


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
) -> None:
    df = df[column_names]
    rows = df.shape[0]
    batch_size = 1000
    insert_query = f"""INSERT INTO {target_table}
({', '.join(quote_identifier(name) for name in column_names)})
VALUES({', '.join('?' for _ in range(len(column_names)))})"""
    index = 0
    while index < rows:
        values = [
            normalize_row(row) 
            for row in df.iloc[index:index+batch_size].itertuples(index=False, name=None)
        ]
        cursor.executemany(insert_query, values)
        index += batch_size


def write_dataframe(
    conn: Connection, 
    df: pd.DataFrame,
    column_names: list[str],
    import_config: ImportConfig
) -> None:
    target_table = (
            f"{quote_identifier(import_config.schema)}."
            f"{quote_identifier(import_config.table)}"
    )
    with conn.cursor() as cursor:
        if import_config.mode == ImportMode.REPLACE:
            cursor.execute(f"DELETE FROM {target_table}")
        insert_dataframe(cursor, target_table, df, column_names)


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
) -> None:
    non_key_columns = [
        column
        for column in column_names
        if column not in key_columns
    ]
    if not non_key_columns:
        return

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


def insert_missing_rows(
    cursor: Cursor,
    column_names: list[str],
    key_columns: tuple[str, ...],
    target_table: str,
)-> None:
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


def upsert_dataframe(
    conn: Connection,
    df: pd.DataFrame,
    column_names: list[str],
    import_config: ImportConfig
) -> None:

    target_table = (
        f"{quote_identifier(import_config.schema)}."
        f"{quote_identifier(import_config.table)}"
    )

    with conn.cursor() as cursor:
        create_temp_table(cursor, column_names, target_table)
        insert_dataframe(cursor, TEMP_TABLE, df, column_names)

        validate_upsert_matches(cursor, import_config, target_table)
        update_existing_rows(cursor, column_names, import_config.key_columns, target_table)

        insert_missing_rows(cursor, column_names, import_config.key_columns, target_table)
        cursor.execute(f"DROP TABLE {TEMP_TABLE}")