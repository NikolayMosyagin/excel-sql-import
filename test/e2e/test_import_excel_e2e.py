from pathlib import Path

import pandas as pd
from mssql_python import Connection

from src.import_excel import main


def test_main_imports_excel_from_config(
    monkeypatch,
    tmp_path: Path,
    test_sql_connection_str: str,
    sql_connection: Connection,
    test_table: str
):
    monkeypatch.setenv(
        "SQL_CONNECTION_STRING",
        test_sql_connection_str
    )

    data_file = "data.xlsx"
    sheet_name = "sheet1"
    config_path = tmp_path / "imports.toml"
    config_path.write_text(f"""[[imports]]
name = \"test_import\"
file = \"{data_file}\"
sheet = \"{sheet_name}\"
schema = \"dbo\"
table = \"{test_table}\"
mode = \"append\"""", encoding="utf-8")

    pd.DataFrame({
        "ID": [1, 2],
        "Name": ["First", "Second"]
    }).to_excel(tmp_path / data_file, sheet_name=sheet_name, index=False)

    main(
        app_dir=tmp_path,
        config_path=config_path,
        scheduled=False,
        run_id="test_run"
    )

    with sql_connection.cursor() as cursor:
        cursor.execute(f"SELECT ID, Name FROM dbo.{test_table} ORDER BY ID, Name")
        result = list(tuple(row) for row in cursor.fetchall())
            
    assert result == [
        (1, "First"),
        (2, "Second")
    ]


def test_main_scheduled_import_moves_and_archives_file(
    monkeypatch,
    tmp_path: Path,
    test_sql_connection_str: str,
    sql_connection: Connection,
    test_table: str
):
    monkeypatch.setenv(
        "SQL_CONNECTION_STRING",
        test_sql_connection_str
    )
    
    data_file = "data.xlsx"
    data_path = tmp_path / data_file
    sheet_name = "sheet1"
    config_path = tmp_path / "imports.toml"
    config_path.write_text(f"""[[imports]]
name = \"test_import\"
file = \"{data_file}\"
sheet = \"{sheet_name}\"
schema = \"dbo\"
table = \"{test_table}\"
mode = \"append\"""", encoding="utf-8")

    pd.DataFrame({
        "ID": [1, 2],
        "Name": ["First", "Second"]
    }).to_excel(data_path, sheet_name=sheet_name, index=False)

    run_id = "2026-09-21_12-00-00"
    main(
        app_dir=tmp_path,
        config_path=config_path,
        scheduled=True,
        run_id=run_id
    )

    with sql_connection.cursor() as cursor:
        cursor.execute(f"SELECT ID, Name FROM dbo.{test_table} ORDER BY ID, Name")
        result = list(tuple(row) for row in cursor.fetchall())
            
    assert result == [
        (1, "First"),
        (2, "Second")
    ]
    assert not data_path.exists()
    assert not (tmp_path / "processing" / run_id).exists()
    assert (tmp_path / "processed" / run_id / f"001_{data_file}").exists()


def test_main_imports_multiple_entries_from_config(
    monkeypatch,
    tmp_path: Path,
    test_sql_connection_str: str,
    sql_connection: Connection,
    test_table: str,
    test_composite_table: str
):
    monkeypatch.setenv(
        "SQL_CONNECTION_STRING",
        test_sql_connection_str
    )

    data_file = "data.xlsx"
    sheet_name1 = "sheet1"
    sheet_name2 = "sheet2"
    config_path = tmp_path / "imports.toml"
    config_path.write_text(f"""[[imports]]
name = \"test_import\"
file = \"{data_file}\"
sheet = \"{sheet_name1}\"
schema = \"dbo\"
table = \"{test_table}\"
mode = \"append\"

[[imports]]
name = \"test_import2\"
file = \"{data_file}\"
sheet = \"{sheet_name2}\"
schema = \"dbo\"
table = \"{test_composite_table}\"
mode = \"append\"""", encoding="utf-8")

    with pd.ExcelWriter(tmp_path / data_file) as writer:
        pd.DataFrame({
                "ID": [1, 2],
                "Name": ["First", "Second"]
        }).to_excel(writer, sheet_name=sheet_name1, index=False)
        pd.DataFrame({
            "ID": [10, 20, 30],
            "Category": [100, 200, 300],
            "Name": ["Name1", "Name2", "Name3"]
        }).to_excel(writer, sheet_name=sheet_name2, index=False)

    main(
        app_dir=tmp_path,
        config_path=config_path,
        scheduled=False,
        run_id="test_run"
    )

    with sql_connection.cursor() as cursor:
        cursor.execute(f"SELECT ID, Name FROM dbo.{test_table} ORDER BY ID, Name")
        first_result = list(tuple(row) for row in cursor.fetchall())
        cursor.execute(f"SELECT ID, Category, Name FROM dbo.{test_composite_table} ORDER BY ID, Category, Name")
        second_result = list(tuple(row) for row in cursor.fetchall())
            
    assert first_result == [
        (1, "First"),
        (2, "Second")
    ]
    assert second_result == [
        (10, 100, "Name1"),
        (20, 200, "Name2"),
        (30, 300, "Name3")
    ]