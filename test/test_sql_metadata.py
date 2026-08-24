from unittest.mock import MagicMock

import pytest

from src.sql_meta_column import SqlMetaColumn
from src.import_config import ImportConfig
from src.sql_metadata import validate_target_tables, get_sql_meta_columns


def test_validate_target_tables_accept_existing_table():
    cursor_mock = MagicMock()
    cursor_mock.__enter__.return_value = cursor_mock
    cursor_mock.fetchone.return_value = (1, )

    conn_mock = MagicMock()
    conn_mock.cursor.return_value = cursor_mock

    import_config = ImportConfig("config1", "file1.xlsx", "sheet1", "schema1", "table1")
    validate_target_tables(conn_mock, [import_config])

    cursor_mock.execute.assert_called_once()
    args, _ = cursor_mock.execute.call_args
    assert args[1] == {
        "schema": "schema1",
        "table": "table1"
    }


def test_validate_target_tables_reject_missing_table():
    cursor_mock = MagicMock()
    cursor_mock.__enter__.return_value = cursor_mock
    cursor_mock.fetchone.return_value = None

    conn_mock = MagicMock()
    conn_mock.cursor.return_value = cursor_mock
    import_config = ImportConfig("config1", "file1.xlsx", "sheet1", "schema1", "table1")

    with pytest.raises(ValueError, match="Target table 'schema1.table1' does not exist."):
        validate_target_tables(conn_mock, [import_config])


def test_validate_target_tables_reject_missing_later_table():
    cursor_mock = MagicMock()
    cursor_mock.__enter__.return_value = cursor_mock
    cursor_mock.fetchone.side_effect = [
        (1, ),
        None
    ]

    conn_mock = MagicMock()
    conn_mock.cursor.return_value = cursor_mock
    import_configs = [
        ImportConfig("config1", "file1.xlsx", "sheet1", "schema1", "table1"),
        ImportConfig("config2", "file2.xlsx", "sheet2", "schema2", "table2"),
    ]
    with pytest.raises(ValueError, match="Target table 'schema2.table2' does not exist."):
        validate_target_tables(conn_mock, import_configs)


def test_get_sql_meta_columns_accept_one_config():
    cursor_mock = MagicMock()
    cursor_mock.__enter__.return_value = cursor_mock
    cursor_mock.fetchall.return_value = [
        ("column1", "int", 0, 0, 0, False), 
        ("column2", "bigint", 0, 0, 0, False)
    ]

    conn_mock = MagicMock()
    conn_mock.cursor.return_value = cursor_mock

    import_config = ImportConfig("config1", "file1.xlsx", "sheet1", "schema1", "table1")
    sql_columns = get_sql_meta_columns(conn_mock, [import_config])

    cursor_mock.execute.assert_called_once()
    args, _ = cursor_mock.execute.call_args
    assert args[1] == {
        "schema": "schema1",
        "table": "table1"
    }
    assert sql_columns == [
        [
            SqlMetaColumn("column1", "int", 0, 0, 0, False),
            SqlMetaColumn("column2", "bigint", 0, 0, 0, False)
        ]
    ]


def test_get_sql_meta_columns_accept_multiple_configs():
    cursor_mock = MagicMock()
    cursor_mock.__enter__.return_value = cursor_mock
    cursor_mock.fetchall.side_effect = [
        [("column1", "int", 0, 0, 0, False), ("column2", "bigint", 0, 0, 0, False)],
        [("column3", "int", 0, 10, 0, True), ("column4", "bigint", 11, 0, 30, False)],
    ]

    import_configs = [
        ImportConfig("config1", "file1.xlsx", "sheet1", "schema1", "table1"),
        ImportConfig("config2", "file2.xlsx", "sheet2", "schema2", "table2"),
    ]
    conn_mock = MagicMock()
    conn_mock.cursor.return_value = cursor_mock
    sql_columns = get_sql_meta_columns(conn_mock, import_configs)
    assert sql_columns == [
        [
            SqlMetaColumn("column1", "int", 0, 0, 0, False),
            SqlMetaColumn("column2", "bigint", 0, 0, 0, False),
        ],
        [
            SqlMetaColumn("column3", "int", 0, 10, 0, True),
            SqlMetaColumn("column4", "bigint", 11, 0, 30, False),
        ]
    ]

    calls = cursor_mock.execute.call_args_list
    assert calls[0].args[1] == {
        "schema": "schema1",
        "table": "table1",
    }

    assert calls[1].args[1] == {
        "schema": "schema2",
        "table": "table2",
    }