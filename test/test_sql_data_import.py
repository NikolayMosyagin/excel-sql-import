from unittest.mock import MagicMock, patch

import pytest
import pandas as pd

from src.sql_data_import import (
    TEMP_TABLE,
    normalize_row,
    build_key_match_condition,
    insert_dataframe,
    write_dataframe,
    create_temp_table,
    validate_upsert_matches,
    update_existing_rows,
    insert_missing_rows,
    upsert_dataframe
)
from src.import_config import ImportConfig, ImportMode


@pytest.mark.parametrize(
    "source_value, expected_value",
    [
        (("abc", 2, 10.0), ("abc", 2, 10.0)),
        (("abc", None, 2), ("abc", None, 2)),
        (("abc", float("nan"), -1), ("abc", None, -1)),
        (("abc", pd.NaT, 0), ("abc", None, 0)),
    ]
)
def test_normalize_row(source_value: tuple, expected_value: tuple):
    assert normalize_row(source_value) == expected_value


@pytest.mark.parametrize(
    "source_value, expected_value",
    [
        (("ID",), "source.[ID] = target.[ID]"),
        (("ReportDate", "Department"), "source.[ReportDate] = target.[ReportDate] AND source.[Department] = target.[Department]"),
        (("Test]Column",), "source.[Test]]Column] = target.[Test]]Column]")
    ]
)
def test_build_key_match_condition(source_value: tuple[str, ...], expected_value: str):
    assert build_key_match_condition(source_value) == expected_value


def test_insert_dataframe_imports_rows_in_batches():
    target_table = "[schema1].[table1]"
    column_names = ["column1"]
    df = pd.DataFrame({"column1": range(2001)})
    cursor_mock = MagicMock()

    insert_dataframe(cursor_mock, target_table, df, column_names)

    assert cursor_mock.executemany.call_count == 3
    calls = cursor_mock.executemany.call_args_list
    assert len(calls[0].args[1]) == 1000
    assert len(calls[1].args[1]) == 1000
    assert len(calls[2].args[1]) == 1


def test_insert_dataframe_inserts_rows():
    target_table = "[schema1].[table1]"
    df = pd.DataFrame({
        "column2": [10, None],
        "column1": ["value1", "value2"],
    })
    column_names = ["column1", "column2"]
    cursor_mock = MagicMock()

    insert_dataframe(cursor_mock, target_table, df, column_names)

    cursor_mock.executemany.assert_called_once()
    insert_query, values = cursor_mock.executemany.call_args.args
    assert "[column1], [column2]" in insert_query
    assert "VALUES(?, ?)" in insert_query
    assert values == [
        ("value1", 10.0),
        ("value2", None),
    ]


def test_write_dataframe_deletes_and_inserts_rows_for_replace():
    cursor_mock = MagicMock()
    cursor_mock.__enter__.return_value = cursor_mock
    
    conn_mock = MagicMock()
    conn_mock.cursor.return_value = cursor_mock

    df = pd.DataFrame({"column1": [1, 2]})
    column_names = ["column1"]
    import_config = ImportConfig("config1", "test.xlsx", "sheet1", "schema1", "table1", ImportMode.REPLACE)

    with patch("src.sql_data_import.insert_dataframe") as insert_mock:
        write_dataframe(conn_mock, df, column_names, import_config)

    cursor_mock.execute.assert_called_once_with(
        "DELETE FROM [schema1].[table1]"
    )
    insert_mock.assert_called_once_with(
        cursor_mock,
        "[schema1].[table1]",
        df,
        column_names
    )


def test_write_dataframe_only_inserts_rows_for_append():
    cursor_mock = MagicMock()
    cursor_mock.__enter__.return_value = cursor_mock
    
    conn_mock = MagicMock()
    conn_mock.cursor.return_value = cursor_mock

    df = pd.DataFrame({"column1": [1, 2]})
    column_names = ["column1"]
    import_config = ImportConfig("config1", "test.xlsx", "sheet1", "schema1", "table1", ImportMode.APPEND)
    with patch("src.sql_data_import.insert_dataframe") as insert_mock:
        write_dataframe(conn_mock, df, column_names, import_config)

    cursor_mock.execute.assert_not_called()
    insert_mock.assert_called_once_with(
        cursor_mock,
        "[schema1].[table1]",
        df,
        column_names
    )


def test_create_temp_table_creates_table_with_columns():
    cursor_mock = MagicMock()
    column_names = ["column1", "column2"]
    target_table = "[schema1].[table1]"
    create_temp_table(cursor_mock, column_names, target_table)

    cursor_mock.execute.assert_called_once()
    sql_query = cursor_mock.execute.call_args.args[0]
    assert f"INTO {TEMP_TABLE}" in sql_query
    assert "[column1], [column2]" in sql_query
    assert f"FROM {target_table}" in sql_query 


def test_validate_upsert_matches_accepts_unambiguous_matches():
    cursor_mock = MagicMock()
    cursor_mock.fetchone.return_value = None
    import_config = ImportConfig("config1", "test.xlsx", "sheet1", "schema1", "table1", ImportMode.UPSERT, ("ID",))
    target_table = f"[{import_config.schema}].[{import_config.table}]"
    validate_upsert_matches(cursor_mock, import_config, target_table)
    cursor_mock.execute.assert_called_once()


def test_validate_upsert_matches_rejects_multiple_target_matches():
    cursor_mock = MagicMock()
    cursor_mock.fetchone.return_value = (10, 2)
    import_config = ImportConfig("config1", "test.xlsx", "sheet1", "schema1", "table1", ImportMode.UPSERT, ("ID",))
    target_table = f"[{import_config.schema}].[{import_config.table}]"
    with pytest.raises(ValueError, match=r"UPSERT key \(ID=10\) matches 2 rows"):
        validate_upsert_matches(cursor_mock, import_config, target_table)


def test_validate_upsert_matches_reports_composite_key_values():
    cursor_mock = MagicMock()
    cursor_mock.fetchone.return_value = (10, "Sales", 3)
    import_config = ImportConfig("config1", "test.xlsx", "sheet1", "schema1", "table1", ImportMode.UPSERT, ("ID1", "ID2"))
    target_table = f"[{import_config.schema}].[{import_config.table}]"
    with pytest.raises(ValueError, match=r"UPSERT key \(ID1=10, ID2=Sales\) matches 3 rows"):
        validate_upsert_matches(cursor_mock, import_config, target_table)


def test_update_existing_rows_updates_non_key_columns():
    cursor_mock = MagicMock()
    column_names = ["ID", "Name", "Value"]
    key_columns = ("ID",)
    target_table = "[schema1].[table1]"
    update_existing_rows(cursor_mock, column_names, key_columns, target_table)
    cursor_mock.execute.assert_called_once()
    sql_query = cursor_mock.execute.call_args.args[0]
    set_part = sql_query.split("SET", 1)[1].split("FROM", 1)[0]
    join_part = sql_query.split("JOIN", 1)[1]
    assert "target.[Name] = source.[Name]" in set_part
    assert "target.[Value] = source.[Value]" in set_part
    assert "target.[ID] = source.[ID]" not in set_part

    assert "source.[ID] = target.[ID]" in join_part


def test_update_existing_rows_does_nothing_when_all_columns_are_keys():
    cursor_mock = MagicMock()
    column_names = ["ID", "Name"]
    key_columns = ("ID", "Name")
    target_table = "[schema1].[table1]"
    update_existing_rows(cursor_mock, column_names, key_columns, target_table)
    cursor_mock.execute.assert_not_called()


def test_insert_missing_rows_builds_insert_for_missing_keys():
    cursor_mock = MagicMock()
    column_names = ["ID", "Name", "Value"]
    key_columns = ("ID",)
    target_table = f"[schema1].[table1]"
    insert_missing_rows(cursor_mock, column_names, key_columns, target_table)
    cursor_mock.execute.assert_called_once()
    sql_query = cursor_mock.execute.call_args.args[0]
    assert f"INSERT INTO {target_table}" in sql_query
    assert f"FROM {TEMP_TABLE} AS source" in sql_query
    assert "WHERE source.[ID] = target.[ID]" in sql_query
    assert "WHERE NOT EXISTS" in sql_query
    select_first_split = sql_query.split("SELECT", 1)[1].split("FROM", 1)[0]
    assert "source.[ID], source.[Name], source.[Value]" in select_first_split
    insert_part = sql_query.split("SELECT", 1)[0]
    assert "[ID], [Name], [Value]" in insert_part


def test_upsert_dataframe_runs_all_upsert_steps():
    cursor_mock = MagicMock()
    cursor_mock.__enter__.return_value = cursor_mock
    
    conn_mock = MagicMock()
    conn_mock.cursor.return_value = cursor_mock

    df = pd.DataFrame({
        "ID": [1, 2],
        "Name": ["Name Old1", "Name Old2"]
    })
    column_names = ["ID", "Name"]
    import_config = ImportConfig("config1", "test.xlsx", "sheet1", "schema1", "table1", ImportMode.UPSERT, ("ID",))
    with (
        patch("src.sql_data_import.create_temp_table") as create_mock,
        patch("src.sql_data_import.insert_dataframe") as insert_mock,
        patch("src.sql_data_import.validate_upsert_matches") as validate_mock,
        patch("src.sql_data_import.update_existing_rows") as update_mock,
        patch("src.sql_data_import.insert_missing_rows") as insert_missing_mock,
    ):
        upsert_dataframe(conn_mock, df, column_names, import_config)

    create_mock.assert_called_once_with(cursor_mock, column_names, "[schema1].[table1]")
    insert_mock.assert_called_once_with(cursor_mock, TEMP_TABLE, df, column_names)
    validate_mock.assert_called_once_with(cursor_mock, import_config, "[schema1].[table1]")
    update_mock.assert_called_once_with(cursor_mock, column_names, import_config.key_columns, "[schema1].[table1]")
    insert_missing_mock.assert_called_once_with(cursor_mock, column_names, import_config.key_columns, "[schema1].[table1]")
    cursor_mock.execute.assert_called_once_with(f"DROP TABLE {TEMP_TABLE}")


def test_upsert_dataframe_stops_when_match_validation_fails():
    cursor_mock = MagicMock()
    cursor_mock.__enter__.return_value = cursor_mock
    
    conn_mock = MagicMock()
    conn_mock.cursor.return_value = cursor_mock

    df = pd.DataFrame({
        "ID": [1, 2],
        "Name": ["Name Old1", "Name Old2"]
    })
    column_names = ["ID", "Name"]
    import_config = ImportConfig("config1", "test.xlsx", "sheet1", "schema1", "table1", ImportMode.UPSERT, ("ID",))
    with (
        patch("src.sql_data_import.create_temp_table") as create_mock,
        patch("src.sql_data_import.insert_dataframe") as insert_mock,
        patch("src.sql_data_import.validate_upsert_matches") as validate_mock,
        patch("src.sql_data_import.update_existing_rows") as update_mock,
        patch("src.sql_data_import.insert_missing_rows") as insert_missing_mock,
    ):
        validate_mock.side_effect = ValueError("Invalid match")
        with pytest.raises(ValueError, match="Invalid match"):
            upsert_dataframe(conn_mock, df, column_names, import_config)

    create_mock.assert_called_once_with(cursor_mock, column_names, "[schema1].[table1]")
    insert_mock.assert_called_once_with(cursor_mock, TEMP_TABLE, df, column_names)
    validate_mock.assert_called_once_with(cursor_mock, import_config, "[schema1].[table1]")
    update_mock.assert_not_called()
    insert_missing_mock.assert_not_called()
    cursor_mock.execute.assert_not_called()