from pathlib import Path
import os
import tomllib
import pandas as pd
from dotenv import load_dotenv

from mssql_python import connect, Connection

from src.import_config import ImportConfig


def read_imports(root: Path) -> list[ImportConfig]:
    imports_path = root / 'config' / 'imports.toml'
    IMPORTS_KEY = 'imports'
    if not imports_path.exists():
        raise FileNotFoundError(f"Configuration file not found: '{imports_path}'.")
    
    with open(imports_path, "rb") as imports_file:
        data = tomllib.load(imports_file)

    if IMPORTS_KEY not in data:
        raise ValueError(f"Required configuration key '{IMPORTS_KEY}' is missing.")

    imports = data[IMPORTS_KEY]
    if not isinstance(imports, list):
        raise TypeError(f"Configuration key '{IMPORTS_KEY}' must be a list.")
    if not imports:
        raise ValueError(f"Configuration key '{IMPORTS_KEY}' cannot be empty.")
    
    import_configs: list[ImportConfig] = []
    for import_data in imports:
        if not isinstance(import_data, dict):
            raise TypeError(f"Import configuration must be a dictionary.")
        try:
            import_configs.append(ImportConfig(**import_data))
        except (TypeError, ValueError) as original_error:
            raise ValueError(
                f"Invalid import configuration '{import_data.get('name', 'unknown')}':\n"
                f"{original_error}"
            ) from original_error
    return import_configs


def validate_import_sources(root: Path, import_configs: list[ImportConfig]) -> None:
    for import_config in import_configs:
        source_file = root / import_config.file
        if not source_file.exists():
            raise FileNotFoundError(f"Source file not found: '{source_file}'.")
    
        if source_file.is_dir():
            raise IsADirectoryError(f"Expected a file, but found a directory: '{source_file}'.")


def validate_excel_sources(root: Path, import_configs: list[ImportConfig]) -> None:
    for import_config in import_configs:
        source_file = root / import_config.file
        with pd.ExcelFile(source_file, engine='openpyxl') as excel_file:
            if import_config.sheet not in excel_file.sheet_names:
                raise ValueError(f"Source file '{source_file}' doesn't contain sheet '{import_config.sheet}'.")
            df = excel_file.parse(sheet_name=import_config.sheet, nrows=1)
        
        if df.empty:
            raise ValueError(f"Sheet '{import_config.sheet}' in source file '{source_file}' is empty.")


def validate_target_tables(conn: Connection, import_configs: list[ImportConfig]) -> None:
    check_query = """
SELECT 1
FROM sys.tables AS t
JOIN sys.schemas as s
	ON s.schema_id = t.schema_id
WHERE s.name = %(schema)s
	AND t.name = %(table)s"""
    for import_config in import_configs:
        with conn.cursor() as cursor:
            cursor.execute(check_query, {'schema': import_config.schema, 'table': import_config.table})
            row_data = cursor.fetchone()
            if row_data is None:
                raise ValueError(f"Target table '{import_config.schema}.{import_config.table}' does not exist.")


def validate_target_columns(root: Path, conn: Connection, import_configs: list[ImportConfig]) -> None:
    get_columns_query = """
SELECT c.name
FROM sys.columns as c
JOIN sys.tables as t
    ON c.object_id = t.object_id
JOIN sys.schemas as s
    ON t.schema_id = s.schema_id
WHERE s.name = %(schema)s
    AND t.name = %(table)s
    AND c.is_identity = 0
    AND c.is_computed = 0
ORDER BY c.column_id"""
    for import_config in import_configs:
        source_file = root / import_config.file
        df = pd.read_excel(
            source_file, 
            sheet_name=import_config.sheet,
            nrows=0,
            engine="openpyxl"
        )
        excel_columns = set(df.columns.to_list())
        with conn.cursor() as cursor:
            cursor.execute(get_columns_query, {'schema': import_config.schema, 'table': import_config.table})
            sql_columns = {row[0] for row in cursor.fetchall()}

        missing_columns = sql_columns - excel_columns
        extra_columns = excel_columns - sql_columns
        errors = []
        if missing_columns:
            errors.append(
                f"Excel source is missing columns required by "
                f"'{import_config.schema}.{import_config.table}': "
                f"{', '.join(sorted(missing_columns))}."
            )
        if extra_columns:
            errors.append(
                f"Excel source contains columns not present in "
                f"'{import_config.schema}.{import_config.table}': "
                f"{', '.join(sorted(extra_columns))}."
            )
        if errors:
            raise ValueError(f"Import '{import_config.name}':\n" + "\n".join(errors))


def import_excel_data(root: Path, conn: Connection, import_config: ImportConfig) -> None:
    source_file = root / import_config.file
    df = pd.read_excel(source_file, sheet_name=import_config.sheet, engine="openpyxl")
    rows = df.shape[0]
    target_table = (
        f"{quote_identifier(import_config.schema)}."
        f"{quote_identifier(import_config.table)}"
    )
    column_names = df.columns.to_list()
    batch_size = 1000
    delete_query = f"DELETE FROM {target_table}"
    insert_query = f"""
INSERT INTO {target_table}
({', '.join(quote_identifier(s) for s in column_names)})
VALUES({', '.join('?' for _ in range(len(column_names)))})"""
    try:
        with conn.cursor() as cursor:
            cursor.execute(delete_query)
            index = 0
            while index < rows:
                values = [
                    normalize_row(row) 
                    for row in df.iloc[index:index+batch_size].itertuples(index=False, name=None)
                ]
                cursor.executemany(insert_query, values)
                index += batch_size
            conn.commit()
    except Exception:
        conn.rollback()
        raise


def quote_identifier(identifier: str) -> str:
    return f"[{identifier.replace(']', ']]')}]"


def normalize_row(row: tuple) -> tuple:
    return tuple(None if pd.isna(value) else value for value in row)


root_path = Path(__file__).resolve().parents[1]
load_dotenv()
import_configs = read_imports(root_path)
validate_import_sources(root_path, import_configs)
validate_excel_sources(root_path, import_configs)
with connect(os.getenv("SQL_CONNECTION_STRING")) as conn:
    validate_target_tables(conn, import_configs)
    validate_target_columns(root_path, conn, import_configs)

    for import_config in import_configs:
        import_excel_data(root_path, conn, import_config)


print("Done!")