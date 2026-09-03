from pathlib import Path
import os
import sys
from dotenv import load_dotenv

from mssql_python import connect, Connection

from src.import_config import ImportConfig, ImportMode
from src.sql_meta_column import SqlMetaColumn
from src.config_loader import read_imports
from src.import_source_validators import validate_excel_sources, validate_import_sources
from src.excel_data_validators import validate_excel_data, validate_target_columns
from src.sql_metadata import get_sql_meta_columns, validate_target_tables
from src.sql_data_import import write_dataframe, upsert_dataframe
from src.excel_utils import read_excel_dataframe


def get_root_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent

    return Path(__file__).resolve().parents[1]

    
def import_excel_data(
    root: Path, 
    conn: Connection, 
    sql_meta_columns: list[SqlMetaColumn], 
    import_config: ImportConfig
) -> None:
    source_file = root / import_config.file

    df = read_excel_dataframe(
        source_file,
        import_config.sheet,
        import_config.column_mapping
    )

    column_names = [column.name for column in sql_meta_columns]

    if import_config.mode == ImportMode.UPSERT:
        upsert_dataframe(conn, df, column_names, import_config)
    else:
        write_dataframe(conn, df, column_names, import_config)


def import_all_data(
    root: Path,
    conn: Connection, 
    import_configs: list[ImportConfig],
    sql_columns: list[list[SqlMetaColumn]]
) -> None:
    try:
        for import_config, sql_column in zip(import_configs, sql_columns, strict=True):
            import_excel_data(root, conn, sql_column, import_config)
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def main():
    root_path = get_root_path()
    load_dotenv(root_path / ".env")
    import_configs = read_imports(root_path)
    validate_import_sources(root_path, import_configs)
    validate_excel_sources(root_path, import_configs)
    sql_connection_string = os.getenv("SQL_CONNECTION_STRING")
    if sql_connection_string is None or sql_connection_string.strip() == "":
        raise ValueError("Required environment variable 'SQL_CONNECTION_STRING' is not set or is empty.")
    
    with connect(sql_connection_string) as conn:
        validate_target_tables(conn, import_configs)
        sql_columns = get_sql_meta_columns(conn, import_configs)
        for import_config, sql_column in zip(import_configs, sql_columns, strict=True):
            validate_target_columns(root_path, sql_column, import_config)
            validate_excel_data(root_path, sql_column, import_config)

        import_all_data(root_path, conn, import_configs, sql_columns)
  
    print("Done!")


if __name__ == '__main__':
    main()