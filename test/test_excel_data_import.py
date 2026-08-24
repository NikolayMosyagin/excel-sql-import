from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.sql_meta_column import SqlMetaColumn
from src.import_excel import (
    quote_identifier,
    normalize_row,
    import_excel_data,
    import_all_data
)
from src.import_config import ImportConfig


@pytest.mark.parametrize(
    "source_value, target_value",
    [
        ("dbo", "[dbo]"),
        ("ReportData", "[ReportData]"),
        ("a]b", "[a]]b]"),
    ]
)
def test_quote_identifier(source_value: str, target_value: str):
    assert quote_identifier(source_value) == target_value


@pytest.mark.parametrize(
    "source_value, target_value",
    [
        (("abc", 2, 10.0), ("abc", 2, 10.0)),
        (("abc", None, 2), ("abc", None, 2)),
        (("abc", float("nan"), -1), ("abc", None, -1)),
        (("abc", pd.NaT, 0), ("abc", None, 0)),
    ]
)
def test_normalize_row(source_value: tuple, target_value: tuple):
    assert normalize_row(source_value) == target_value


def test_import_excel_data_imports_rows(tmp_path: Path):
    import_config = ImportConfig("config1", "test.xlsx", "sheet1", "schema1", "table1")

    sql_columns = [
        SqlMetaColumn("column1", "nvarchar", 100, 0, 0, False),
        SqlMetaColumn("column2", "int", 0, 0, 0, True),
    ]

    data = {
        "column2": [10, None],
        "column1": ["value1", "value2"],
    }

    file_path = tmp_path / import_config.file
    pd.DataFrame(data).to_excel(file_path, sheet_name=import_config.sheet, index=False,)

    cursor_mock = MagicMock()
    cursor_mock.__enter__.return_value = cursor_mock

    conn_mock = MagicMock()
    conn_mock.cursor.return_value = cursor_mock

    import_excel_data(tmp_path, conn_mock, sql_columns, import_config)

    cursor_mock.execute.assert_called_once_with(
        "DELETE FROM [schema1].[table1]"
    )
    cursor_mock.executemany.assert_called_once()
    insert_query, values = cursor_mock.executemany.call_args.args
    assert "[column1], [column2]" in insert_query
    assert "VALUES(?, ?)" in insert_query
    assert values == [
        ("value1", 10.0),
        ("value2", None),
    ]
    conn_mock.commit.assert_not_called()
    conn_mock.rollback.assert_not_called()


def test_import_excel_data_propagates_insert_error(tmp_path: Path):
    import_config = ImportConfig("config1","test.xlsx","sheet1", "schema1", "table1")

    sql_columns = [
        SqlMetaColumn("column1", "int", 0, 0, 0, False),
    ]

    file_path = tmp_path / import_config.file
    pd.DataFrame({"column1": [1, 2]}).to_excel(file_path, sheet_name=import_config.sheet, index=False)

    cursor_mock = MagicMock()
    cursor_mock.__enter__.return_value = cursor_mock
    cursor_mock.executemany.side_effect = RuntimeError("Insert failed")

    conn_mock = MagicMock()
    conn_mock.cursor.return_value = cursor_mock

    with pytest.raises(RuntimeError, match="Insert failed"):
        import_excel_data(tmp_path, conn_mock, sql_columns, import_config)
    conn_mock.rollback.assert_not_called()
    conn_mock.commit.assert_not_called()


def test_import_excel_data_imports_rows_in_batches(tmp_path: Path):
    import_config = ImportConfig("config1", "test.xlsx", "sheet1", "schema1", "table1")

    sql_columns = [
        SqlMetaColumn("column1", "int", 0, 0, 0, False),
    ]

    file_path = tmp_path / import_config.file
    pd.DataFrame({ "column1": range(2001)}).to_excel(file_path, sheet_name=import_config.sheet, index=False)

    cursor_mock = MagicMock()
    cursor_mock.__enter__.return_value = cursor_mock

    conn_mock = MagicMock()
    conn_mock.cursor.return_value = cursor_mock

    import_excel_data(tmp_path, conn_mock, sql_columns, import_config)

    assert cursor_mock.executemany.call_count == 3
    calls = cursor_mock.executemany.call_args_list
    assert len(calls[0].args[1]) == 1000
    assert len(calls[1].args[1]) == 1000
    assert len(calls[2].args[1]) == 1
    conn_mock.commit.assert_not_called()
    conn_mock.rollback.assert_not_called()


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
    conn_mock.rollback.assert_called_once()
    conn_mock.commit.assert_not_called()