from pathlib import Path

from mssql_python import Connection
import pandas as pd
import pytest

from src.import_task import ImportTask
from src.import_config import ImportConfig, ImportMode
from src.sql_meta_column import SqlMetaColumn
from src.import_excel import import_all_data

def test_import_all_data_rolls_back_all_imports_when_later_import_fails(
    sql_connection: Connection,
    test_table: str,
    tmp_path: Path
):
    with sql_connection.cursor() as cursor:
        cursor.execute(f"INSERT INTO dbo.{test_table} VALUES (100, 'Existing')")
    sql_connection.commit()

    import_tasks = [
        ImportTask(
            ImportConfig(
                "import1",
                "test1.xlsx",
                "sheet1",
                "dbo",
                test_table,
                mode=ImportMode.APPEND
            ),
            tmp_path / "test1.xlsx",
            tmp_path / "test1.xlsx"
        ),
        ImportTask(
            ImportConfig(
                "import2",
                "test2.xlsx",
                "sheet1",
                "dbo",
                test_table,
                mode=ImportMode.APPEND
            ),
            tmp_path / "test2.xlsx",
            tmp_path / "test2.xlsx"
        )
    ]

    pd.DataFrame({
        "ID": [1],
        "Name": ["NewA"]
    }).to_excel(import_tasks[0].working_file, sheet_name="sheet1", index=False)

    pd.DataFrame({
        "ID": ["sts"],
        "Name": ["NewB"]
    }).to_excel(import_tasks[1].working_file, sheet_name="sheet1", index=False)

    sql_meta_columns = [
        [SqlMetaColumn("ID", "int", -1, -1, -1, False), SqlMetaColumn("Name", "nvarchar", 100, -1, -1, True)],
        [SqlMetaColumn("ID", "int", -1, -1, -1, False), SqlMetaColumn("Name", "nvarchar", 100, -1, -1, True)]
    ]

    with pytest.raises(Exception):
        import_all_data(sql_connection, import_tasks, sql_meta_columns)

    sql_query = f"""SELECT ID, Name FROM dbo.{test_table} ORDER BY ID, Name"""
    with sql_connection.cursor() as cursor:
        cursor.execute(sql_query)
        result = list(tuple(row) for row in cursor.fetchall())
        
    assert result == [
        (100, "Existing"),
    ]


def test_import_all_data_commits_all_imports_when_all_succeed(
    sql_connection: Connection,
    test_table: str,
    tmp_path: Path,
):
    with sql_connection.cursor() as cursor:
        cursor.execute(f"INSERT INTO dbo.{test_table} VALUES (100, 'Existing')")
    sql_connection.commit()
    
    import_tasks = [
        ImportTask(
            ImportConfig(
                "import1",
                "test1.xlsx",
                "sheet1",
                "dbo",
                test_table,
                mode=ImportMode.APPEND
            ),
            tmp_path / "test1.xlsx",
            tmp_path / "test1.xlsx"
        ),
        ImportTask(
            ImportConfig(
                "import2",
                "test2.xlsx",
                "sheet1",
                "dbo",
                test_table,
                mode=ImportMode.APPEND
            ),
            tmp_path / "test2.xlsx",
            tmp_path / "test2.xlsx"
        )
    ]
    
    pd.DataFrame({
        "ID": [1, 2],
        "Name": ["NewA", "NewB"]
    }).to_excel(import_tasks[0].working_file, sheet_name="sheet1", index=False)

    pd.DataFrame({
        "ID": [10, 20],
        "Name": ["NewC", "NewA"]
    }).to_excel(import_tasks[1].working_file, sheet_name="sheet1", index=False)

    sql_meta_columns = [
        [SqlMetaColumn("ID", "int", -1, -1, -1, False), SqlMetaColumn("Name", "nvarchar", 100, -1, -1, True)],
        [SqlMetaColumn("ID", "int", -1, -1, -1, False), SqlMetaColumn("Name", "nvarchar", 100, -1, -1, True)]
    ]

    import_all_data(sql_connection, import_tasks, sql_meta_columns)

    sql_query = f"""SELECT ID, Name FROM dbo.{test_table} ORDER BY ID, Name"""
    with sql_connection.cursor() as cursor:
        cursor.execute(sql_query)
        result = list(tuple(row) for row in cursor.fetchall())
        
    assert result == [
        (1, "NewA"),
        (2, "NewB"),
        (10, "NewC"),
        (20, "NewA"),
        (100, "Existing")
    ]