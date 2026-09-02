from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.sql_meta_column import SqlMetaColumn
from src.import_excel import (
    import_excel_data,
    import_all_data
)
from src.import_config import ImportConfig, ImportMode


@pytest.mark.parametrize(
    "mode",
    [ImportMode.REPLACE, ImportMode.APPEND]
)
def test_import_excel_data_uses_write_dataframe_for_non_upsert_mode(tmp_path: Path, mode: ImportMode):
    import_config = ImportConfig("config1", "test.xlsx", "sheet1", "schema1", "table1", mode)
    sql_columns = [
        SqlMetaColumn("column1", "nvarchar", 100, 0, 0, False),
        SqlMetaColumn("column2", "int", 0, 0, 0, True),
    ]

    conn_mock = MagicMock()
    df = pd.DataFrame({
            "column2": [10],
            "column1": ["value1"],
    })
    with (
        patch("src.import_excel.pd.read_excel") as read_excel_mock,
        patch("src.import_excel.upsert_dataframe") as upsert_mock,
        patch("src.import_excel.write_dataframe") as write_mock,
    ):
        read_excel_mock.return_value = df
        import_excel_data(tmp_path, conn_mock, sql_columns, import_config)

    read_excel_mock.assert_called_once_with(
        tmp_path / "test.xlsx",
        sheet_name="sheet1",
        engine="openpyxl"
    )
    write_mock.assert_called_once_with(conn_mock, df, ["column1", "column2"], import_config)
    upsert_mock.assert_not_called()


def test_import_excel_data_uses_upsert_dataframe_for_upsert_mode(tmp_path: Path):
    import_config = ImportConfig("config1", "test.xlsx", "sheet1", "schema1", "table1", ImportMode.UPSERT, ("column1",))
    sql_columns = [
        SqlMetaColumn("column1", "nvarchar", 100, 0, 0, False),
        SqlMetaColumn("column2", "int", 0, 0, 0, True),
    ]

    conn_mock = MagicMock()
    df = pd.DataFrame({
            "column2": [10],
            "column1": ["value1"],
    })
    with (
        patch("src.import_excel.pd.read_excel") as read_excel_mock,
        patch("src.import_excel.upsert_dataframe") as upsert_mock,
        patch("src.import_excel.write_dataframe") as write_mock,
    ):
        read_excel_mock.return_value = df
        import_excel_data(tmp_path, conn_mock, sql_columns, import_config)

    read_excel_mock.assert_called_once_with(
        tmp_path / "test.xlsx",
        sheet_name="sheet1",
        engine="openpyxl"
    )
    upsert_mock.assert_called_once_with(conn_mock, df, ["column1", "column2"], import_config)
    write_mock.assert_not_called()


def test_import_excel_data_uses_xlrd_for_xls(tmp_path: Path):
    import_config = ImportConfig("config1", "test.xls", "sheet1", "schema1", "table1", ImportMode.UPSERT, ("column1",))
    sql_columns = [
        SqlMetaColumn("column1", "nvarchar", 100, 0, 0, False),
        SqlMetaColumn("column2", "int", 0, 0, 0, True),
    ]

    conn_mock = MagicMock()
    df = pd.DataFrame({
            "column2": [10],
            "column1": ["value1"],
    })
    with (
        patch("src.import_excel.pd.read_excel") as read_excel_mock,
        patch("src.import_excel.upsert_dataframe") as upsert_mock,
        patch("src.import_excel.write_dataframe") as write_mock,
    ):
        read_excel_mock.return_value = df
        import_excel_data(tmp_path, conn_mock, sql_columns, import_config)

    read_excel_mock.assert_called_once_with(
        tmp_path / "test.xls",
        sheet_name="sheet1",
        engine="xlrd"
    )
    upsert_mock.assert_called_once_with(conn_mock, df, ["column1", "column2"], import_config)
    write_mock.assert_not_called()


def test_import_all_data_commits_after_all_imports(tmp_path: Path):
    import_configs = [
        ImportConfig("config1", "file1.xlsx", "sheet1", "schema1", "table1"),
        ImportConfig("config2", "file2.xlsx", "sheet2", "schema2", "table2"),
    ]

    sql_columns = [
        [SqlMetaColumn("column1", "int", 0, 0, 0, False)],
        [SqlMetaColumn("column2", "int", 0, 0, 0, False)],
    ]

    conn_mock = MagicMock()

    with patch("src.import_excel.import_excel_data") as import_mock:
        import_all_data(tmp_path, conn_mock, import_configs, sql_columns)

    assert import_mock.call_count == 2
    assert import_mock.call_args_list[0].args == (
        tmp_path,
        conn_mock,
        sql_columns[0],
        import_configs[0]
    )
    assert import_mock.call_args_list[1].args == (
        tmp_path,
        conn_mock,
        sql_columns[1],
        import_configs[1]
    )
    conn_mock.commit.assert_called_once()
    conn_mock.rollback.assert_not_called()


def test_import_all_data_rolls_back_when_import_fails(tmp_path: Path):
    import_configs = [
        ImportConfig("config1", "file1.xlsx", "sheet1", "schema1", "table1"),
        ImportConfig("config2", "file2.xlsx", "sheet2", "schema2", "table2"),
    ]

    sql_columns = [
        [SqlMetaColumn("column1", "int", 0, 0, 0, False)],
        [SqlMetaColumn("column2", "int", 0, 0, 0, False)],
    ]

    conn_mock = MagicMock()

    with patch(
        "src.import_excel.import_excel_data",
        side_effect=[None, RuntimeError("Import failed")]
    ) as import_mock:
        with pytest.raises(RuntimeError, match="Import failed"):
            import_all_data(tmp_path, conn_mock, import_configs, sql_columns)

    assert import_mock.call_count == 2
    assert import_mock.call_args_list[0].args == (
        tmp_path,
        conn_mock,
        sql_columns[0],
        import_configs[0]
    )
    assert import_mock.call_args_list[1].args == (
        tmp_path,
        conn_mock,
        sql_columns[1],
        import_configs[1]
    )
    conn_mock.rollback.assert_called_once()
    conn_mock.commit.assert_not_called()


def test_import_all_data_rolls_back_when_input_lengths_mismatch(tmp_path: Path):
    import_configs = [
        ImportConfig("config1", "file1.xlsx", "sheet1", "schema1", "table1"),
    ]

    sql_columns = [
        [SqlMetaColumn("column1", "int", 0, 0, 0, False)],
        [SqlMetaColumn("column2", "int", 0, 0, 0, False)],
    ]

    conn_mock = MagicMock()

    with patch("src.import_excel.import_excel_data") as import_mock:
        with pytest.raises(ValueError, match="zip()"):
            import_all_data(tmp_path, conn_mock, import_configs, sql_columns)

    import_mock.assert_called_once_with(
        tmp_path,
        conn_mock,
        sql_columns[0],
        import_configs[0]
    )      
    conn_mock.commit.assert_not_called()
    conn_mock.rollback.assert_called_once()