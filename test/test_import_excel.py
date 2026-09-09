from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.sql_meta_column import SqlMetaColumn
from src.import_excel import (
    import_excel_data,
    import_all_data,
    get_config_path,
    parse_args,
    run
)
from src.import_config import ImportConfig, ImportMode


@pytest.mark.parametrize(
    "mode",
    [ImportMode.REPLACE, ImportMode.APPEND]
)
def test_import_excel_data_uses_write_dataframe_for_non_upsert_mode(tmp_path: Path, mode: ImportMode):
    import_config = ImportConfig(
        "config1", 
        "test.xlsx", 
        "sheet1", 
        "schema1", 
        "table1", 
        mode,
        column_mapping={"Дата": "ReportDate"},
        date_formats={"ReportDate": "%d.%m.%Y"}
    )
    sql_columns = [
        SqlMetaColumn("column1", "nvarchar", 100, 0, 0, False),
        SqlMetaColumn("ReportDate", "date", 0, 0, 0, True),
    ]

    conn_mock = MagicMock()
    df = pd.DataFrame({
            "ReportDate": [datetime(1994, 5, 31)],
            "column1": ["value1"],
    })
    data_file = tmp_path / import_config.file
    with (
        patch("src.import_excel.prepare_excel_dataframe") as prepare_excel_mock,
        patch("src.import_excel.upsert_dataframe") as upsert_mock,
        patch("src.import_excel.write_dataframe") as write_mock,
    ):
        prepare_excel_mock.return_value = df
        import_excel_data(data_file, conn_mock, sql_columns, import_config)

    prepare_excel_mock.assert_called_once_with(
        data_file,
        import_config.sheet,
        import_config.column_mapping,
        import_config.date_formats
    )
    write_mock.assert_called_once_with(conn_mock, df, ["column1", "ReportDate"], import_config)
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
    data_file = tmp_path / import_config.file
    with (
        patch("src.import_excel.prepare_excel_dataframe") as prepare_excel_mock,
        patch("src.import_excel.upsert_dataframe") as upsert_mock,
        patch("src.import_excel.write_dataframe") as write_mock,
    ):
        prepare_excel_mock.return_value = df
        import_excel_data(data_file, conn_mock, sql_columns, import_config)

    prepare_excel_mock.assert_called_once_with(
        data_file,
        import_config.sheet,
        import_config.column_mapping,
        import_config.date_formats
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
        tmp_path / import_configs[0].file,
        conn_mock,
        sql_columns[0],
        import_configs[0]
    )
    assert import_mock.call_args_list[1].args == (
        tmp_path / import_configs[1].file,
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
        tmp_path / import_configs[0].file,
        conn_mock,
        sql_columns[0],
        import_configs[0]
    )
    assert import_mock.call_args_list[1].args == (
        tmp_path / import_configs[1].file,
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
        tmp_path / import_configs[0].file,
        conn_mock,
        sql_columns[0],
        import_configs[0]
    )      
    conn_mock.commit.assert_not_called()
    conn_mock.rollback.assert_called_once()


def test_parse_args_returns_none_when_config_not_specified():
    result = parse_args([])
    assert result.config is None


def test_parse_args_accepts_long_config_argument():
    result = parse_args(["--config", "imports.toml"])
    assert result.config == "imports.toml"


def test_parse_args_accepts_short_config_argument():
    result = parse_args(["-c", "imports.toml"])
    assert result.config == "imports.toml"


def test_parse_args_rejects_config_without_value():
    with pytest.raises(SystemExit):
        parse_args(["--config"])


def test_get_config_path_uses_default_config(tmp_path: Path):
    app_dir = tmp_path / "app"
    cur_dir = tmp_path / "cur"
    result = get_config_path(None, app_dir, cur_dir)
    assert result == app_dir / "config" / "imports.toml"


def test_get_config_path_resolves_relative_config_from_current_dir(tmp_path: Path):
    app_dir = tmp_path / "app"
    cur_dir = tmp_path / "cur"
    result = get_config_path("imports.toml", app_dir, cur_dir)
    assert result == cur_dir / "imports.toml"


def test_get_config_path_keeps_absolute_config_path(tmp_path: Path):
    app_dir = tmp_path / "app"
    cur_dir = tmp_path / "cur"
    config_path = tmp_path / "imports.toml"
    result = get_config_path(str(config_path), app_dir, cur_dir)
    assert result == config_path


def test_run_returns_zero_when_import_succeeds():
    with (
        patch("src.import_excel.main") as main_mock,
        patch("src.import_excel.logger.info") as logger_info_mock,
        patch("src.import_excel.logger.exception") as logger_exception_mock
    ):
        result = run()

    assert result == 0
    assert logger_info_mock.call_count == 2
    args_list = logger_info_mock.call_args_list
    assert args_list[0].args[0] == "Import started."
    assert args_list[1].args[0] == "Import completed successfully."
    main_mock.assert_called_once()
    logger_exception_mock.assert_not_called()


def test_run_returns_one_when_import_fails():
    with (
        patch("src.import_excel.main") as main_mock,
        patch("src.import_excel.logger.info") as logger_info_mock,
        patch("src.import_excel.logger.exception") as logger_exception_mock
    ):
        main_mock.side_effect = RuntimeError("Test Error")
        result = run()

    assert result == 1
    logger_info_mock.assert_called_once_with("Import started.")
    main_mock.assert_called_once()
    logger_exception_mock.assert_called_once_with("Import failed.")