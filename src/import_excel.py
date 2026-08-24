from pathlib import Path
import os
import pandas as pd
from dotenv import load_dotenv

from mssql_python import connect, Connection

from src.import_config import ImportConfig
from src.sql_meta_column import SqlMetaColumn
from src.config_loader import read_imports
from src.import_source_validators import validate_excel_sources, validate_import_sources
from src.excel_data_validators import validate_excel_data, validate_target_columns
from src.sql_metadata import get_sql_meta_columns, validate_target_tables


def import_excel_data(
        root: Path, 
        conn: Connection, 
        sql_meta_columns: list[SqlMetaColumn], 
        import_config: ImportConfig
) -> None:
    source_file = root / import_config.file
    df = pd.read_excel(source_file, sheet_name=import_config.sheet, engine="openpyxl")
    column_names = [column.name for column in sql_meta_columns]
    df = df[column_names]

    rows = df.shape[0]
    target_table = (
        f"{quote_identifier(import_config.schema)}."
        f"{quote_identifier(import_config.table)}"
    )

    batch_size = 1000
    delete_query = f"DELETE FROM {target_table}"
    insert_query = f"""
INSERT INTO {target_table}
({', '.join(quote_identifier(name) for name in column_names)})
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

def main():
    root_path = Path(__file__).resolve().parents[1]
    load_dotenv()
    import_configs = read_imports(root_path)
    validate_import_sources(root_path, import_configs)
    validate_excel_sources(root_path, import_configs)
    with connect(os.getenv("SQL_CONNECTION_STRING")) as conn:
        validate_target_tables(conn, import_configs)
        sql_columns = get_sql_meta_columns(conn, import_configs)
        for i, import_config in enumerate(import_configs):
            validate_target_columns(root_path, sql_columns[i], import_config)
            validate_excel_data(root_path, sql_columns[i], import_config)

        for i, import_config in enumerate(import_configs):
            import_excel_data(root_path, conn, sql_columns[i], import_config)
            
    print("Done!")


if __name__ == '__main__':
    main()