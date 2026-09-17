from datetime import datetime
import logging
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
    run,
    main,
    configure_logging,
    create_run_id,
)
from src.import_config import ImportConfig, ImportMode
from src.import_task import ImportTask


@pytest.fixture
def isolated_logging():
    root_logger = logging.getLogger()

    original_handlers = root_logger.handlers[:]
    original_level = root_logger.level

    for handler in original_handlers:
        root_logger.removeHandler(handler)

    yield

    for handler in root_logger.handlers[:]:
        handler.close()
        root_logger.removeHandler(handler)

    for handler in original_handlers:
        root_logger.addHandler(handler)

    root_logger.setLevel(original_level)


@pytest.mark.parametrize(
    "mode",
    [ImportMode.REPLACE, ImportMode.APPEND]
)
def test_import_excel_data_uses_write_dataframe_for_replace_and_append_modes(tmp_path: Path, mode: ImportMode):
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
        patch("src.import_excel.replace_by_columns_dataframe") as replace_mock,
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
    replace_mock.assert_not_called()


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
        patch("src.import_excel.replace_by_columns_dataframe") as replace_mock,
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
    replace_mock.assert_not_called()


def test_import_excel_data_uses_replace_by_columns_dataframe_for_replace_by_columns(tmp_path: Path):
    import_config = ImportConfig(
        "config1",
        "test.xlsx",
        "sheet1",
        "schema1",
        "table1",
        ImportMode.REPLACE_BY_COLUMNS, 
        replace_columns=("column1",))

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
        patch("src.import_excel.replace_by_columns_dataframe") as replace_mock,
    ):
        prepare_excel_mock.return_value = df
        import_excel_data(data_file, conn_mock, sql_columns, import_config)

    prepare_excel_mock.assert_called_once_with(
        data_file,
        import_config.sheet,
        import_config.column_mapping,
        import_config.date_formats
    )
    upsert_mock.assert_not_called()
    write_mock.assert_not_called()
    replace_mock.assert_called_once_with(
        conn_mock,
        df,
        ["column1", "column2"],
        import_config
    )


def test_import_all_data_commits_after_all_imports(tmp_path: Path):
    import_configs = [
        ImportConfig("config1", "file1.xlsx", "sheet1", "schema1", "table1"),
        ImportConfig("config2", "file2.xlsx", "sheet2", "schema2", "table2"),
    ]

    import_tasks = [
        ImportTask(import_config, tmp_path / f"source_{import_config.file}", tmp_path / f"working_{import_config.file}")
        for import_config in import_configs
    ]

    sql_columns = [
        [SqlMetaColumn("column1", "int", 0, 0, 0, False)],
        [SqlMetaColumn("column2", "int", 0, 0, 0, False)],
    ]

    conn_mock = MagicMock()

    with patch("src.import_excel.import_excel_data") as import_mock:
        import_all_data(conn_mock, import_tasks, sql_columns)

    assert import_mock.call_count == 2
    assert import_mock.call_args_list[0].args == (
        import_tasks[0].working_file,
        conn_mock,
        sql_columns[0],
        import_tasks[0].config
    )
    assert import_mock.call_args_list[1].args == (
        import_tasks[1].working_file,
        conn_mock,
        sql_columns[1],
        import_tasks[1].config
    )
    conn_mock.commit.assert_called_once()
    conn_mock.rollback.assert_not_called()


def test_import_all_data_rolls_back_when_import_fails(tmp_path: Path):
    import_configs = [
        ImportConfig("config1", "file1.xlsx", "sheet1", "schema1", "table1"),
        ImportConfig("config2", "file2.xlsx", "sheet2", "schema2", "table2"),
    ]

    import_tasks = [
        ImportTask(import_config, tmp_path / f"source_{import_config.file}", tmp_path / f"working_{import_config.file}")
        for import_config in import_configs
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
            import_all_data(conn_mock, import_tasks, sql_columns)

    assert import_mock.call_count == 2
    assert import_mock.call_args_list[0].args == (
        import_tasks[0].working_file,
        conn_mock,
        sql_columns[0],
        import_tasks[0].config
    )
    assert import_mock.call_args_list[1].args == (
        import_tasks[1].working_file,
        conn_mock,
        sql_columns[1],
        import_tasks[1].config
    )
    conn_mock.rollback.assert_called_once()
    conn_mock.commit.assert_not_called()


def test_import_all_data_rolls_back_when_input_lengths_mismatch(tmp_path: Path):

    import_tasks = [
        ImportTask(
            ImportConfig("config1", "file1.xlsx", "sheet1", "schema1", "table1"), 
            tmp_path / "source_file1.xlsx", 
            tmp_path / "working_file1.xlsx"
        )
    ]

    sql_columns = [
        [SqlMetaColumn("column1", "int", 0, 0, 0, False)],
        [SqlMetaColumn("column2", "int", 0, 0, 0, False)],
    ]

    conn_mock = MagicMock()

    with patch("src.import_excel.import_excel_data") as import_mock:
        with pytest.raises(ValueError, match="zip()"):
            import_all_data(conn_mock, import_tasks, sql_columns)

    import_mock.assert_called_once_with(
        import_tasks[0].working_file,
        conn_mock,
        sql_columns[0],
        import_tasks[0].config
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


def test_parse_args_accepts_scheduled_argument():
    result = parse_args(["--scheduled"])
    assert result.scheduled

def test_parse_args_defaults_to_non_scheduled_mode():
    result = parse_args([])
    assert not result.scheduled


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


def test_run_returns_zero_when_import_succeeds(tmp_path: Path):
    app_dir = tmp_path / "app"
    config_path = tmp_path / "config" / "imports.toml"
    scheduled = True
    run_id = "123"
    with (
        patch("src.import_excel.main") as main_mock,
        patch("src.import_excel.logger.info") as logger_info_mock,
        patch("src.import_excel.logger.exception") as logger_exception_mock
    ):
        result = run(app_dir, config_path, scheduled, run_id)

    assert result == 0
    assert logger_info_mock.call_count == 2
    args_list = logger_info_mock.call_args_list
    assert args_list[0].args[0] == "Import started."
    assert args_list[1].args[0] == "Import completed successfully."
    main_mock.assert_called_once_with(app_dir, config_path, scheduled, run_id)
    logger_exception_mock.assert_not_called()


def test_run_returns_one_when_import_fails(tmp_path: Path):
    app_dir = tmp_path / "app"
    config_path = tmp_path / "config" / "imports.toml"
    run_id = "12"
    scheduled = False
    with (
        patch("src.import_excel.main") as main_mock,
        patch("src.import_excel.logger.info") as logger_info_mock,
        patch("src.import_excel.logger.exception") as logger_exception_mock
    ):
        main_mock.side_effect = RuntimeError("Test Error")
        result = run(app_dir, config_path, scheduled, run_id)

    assert result == 1
    logger_info_mock.assert_called_once_with("Import started.")
    main_mock.assert_called_once_with(app_dir, config_path, scheduled, run_id)
    logger_exception_mock.assert_called_once_with("Import failed.")


def test_configure_logging_without_scheduled_does_not_create_log_file(tmp_path: Path, capsys, isolated_logging):
    run_id = "1"
    configure_logging(False, tmp_path, run_id)

    logging.getLogger("test").info("Test message")

    captured = capsys.readouterr()

    assert "Test message" in captured.err
    assert not (tmp_path / "logs").exists()


def test_configure_logging_scheduled_writes_to_file(tmp_path: Path, capsys, isolated_logging):
    run_id = "1"
    configure_logging(True, tmp_path, run_id)

    logging.getLogger("test").info("Test message")

    captured = capsys.readouterr()

    log_file = tmp_path / "logs" / "import_1.log"

    assert "Test message" in captured.err
    assert log_file.exists()
    assert "Test message" in log_file.read_text(encoding="utf-8")


def test_create_run_id():
    with patch("src.import_excel.datetime") as datetime_mock:
        datetime_mock.now.return_value = datetime(2000, 5, 31, 22, 30, 31)
        result = create_run_id()

    assert result == "2000-05-31_22-30-31"


def test_main_uses_manual_import_tasks_when_not_scheduled(tmp_path: Path):
    app_dir = tmp_path / "app"
    config_path = tmp_path / "config" / "imports.toml"
    run_id = "123"

    import_config = ImportConfig(
        "test",
        "test.xlsx",
        "sheet1",
        "schema1",
        "table1"
    )
    import_configs = [import_config]

    import_tasks = [
        ImportTask(
            import_config,
            tmp_path / "source_test.xlsx",
            tmp_path / "source_test.xlsx"
        )
    ]

    conn_mock = MagicMock()
    sql_columns = [[]]

    with (
        patch("src.import_excel.read_imports", return_value=import_configs),
        patch("src.import_excel.build_manual_import_tasks", return_value=import_tasks) as manual_tasks_mock,
        patch("src.import_excel.build_scheduled_import_tasks") as scheduled_tasks_mock,
        patch("src.import_excel.get_processing_run_dir") as processing_dir_mock,
        patch("src.import_excel.create_processing_run_dir") as create_processing_dir_mock,
        patch("src.import_excel.move_source_files") as move_files_mock,
        patch("src.import_excel.validate_import_sources"),
        patch("src.import_excel.validate_excel_sources"),
        patch("src.import_excel.os.getenv", return_value="connection"),
        patch("src.import_excel.connect") as connect_mock,
        patch("src.import_excel.validate_target_tables"),
        patch("src.import_excel.get_sql_meta_columns", return_value=sql_columns),
        patch("src.import_excel.validate_target_columns"),
        patch("src.import_excel.validate_excel_data"),
        patch("src.import_excel.import_all_data"),
        patch("src.import_excel.get_processed_run_dir") as processed_dir_mock,
        patch("src.import_excel.archive_processing_run") as archive_processing_mock
    ):
        connect_mock.return_value.__enter__.return_value = conn_mock

        main(app_dir, config_path, False, run_id)

    manual_tasks_mock.assert_called_once_with(
        config_path.parent,
        import_configs
    )
    scheduled_tasks_mock.assert_not_called()

    processing_dir_mock.assert_not_called()
    create_processing_dir_mock.assert_not_called()
    move_files_mock.assert_not_called()
    processed_dir_mock.assert_not_called()
    archive_processing_mock.assert_not_called()


def test_main_uses_scheduled_import_tasks_when_scheduled(tmp_path: Path):
    app_dir = tmp_path / "app"
    config_path = tmp_path / "config" / "imports.toml"
    run_id = "123"
    processing_run_dir = config_path.parent / "processing" / run_id
    processed_run_dir = config_path.parent / "processed" / run_id

    import_config = ImportConfig(
        "test",
        "test.xlsx",
        "sheet1",
        "schema1",
        "table1"
    )
    import_configs = [import_config]

    import_tasks = [
        ImportTask(
            import_config,
            tmp_path / "source_test.xlsx",
            processing_run_dir / "001_test.xlsx"
        )
    ]

    conn_mock = MagicMock()
    sql_columns = [[]]

    with (
        patch("src.import_excel.read_imports", return_value=import_configs),
        patch("src.import_excel.build_manual_import_tasks") as manual_tasks_mock,
        patch(
            "src.import_excel.get_processing_run_dir",
            return_value=processing_run_dir
        ) as processing_dir_mock,
        patch(
            "src.import_excel.build_scheduled_import_tasks",
            return_value=import_tasks
        ) as scheduled_tasks_mock,
        patch("src.import_excel.validate_import_sources"),
        patch("src.import_excel.create_processing_run_dir") as create_processing_dir_mock,
        patch("src.import_excel.move_source_files") as move_files_mock,
        patch("src.import_excel.validate_excel_sources"),
        patch("src.import_excel.os.getenv", return_value="connection"),
        patch("src.import_excel.connect") as connect_mock,
        patch("src.import_excel.validate_target_tables"),
        patch("src.import_excel.get_sql_meta_columns", return_value=sql_columns),
        patch("src.import_excel.validate_target_columns"),
        patch("src.import_excel.validate_excel_data"),
        patch("src.import_excel.import_all_data"),
        patch("src.import_excel.get_processed_run_dir", return_value=processed_run_dir) as processed_dir_mock,
        patch("src.import_excel.archive_processing_run") as archive_processing_mock
    ):
        connect_mock.return_value.__enter__.return_value = conn_mock

        main(app_dir, config_path, True, run_id)

    manual_tasks_mock.assert_not_called()

    processing_dir_mock.assert_called_once_with(
        config_path.parent,
        run_id
    )
    scheduled_tasks_mock.assert_called_once_with(
        config_path.parent,
        import_configs,
        processing_run_dir
    )
    create_processing_dir_mock.assert_called_once_with(processing_run_dir)
    move_files_mock.assert_called_once_with(import_tasks)
    processed_dir_mock.assert_called_once_with(
        config_path.parent,
        run_id
    )
    archive_processing_mock.assert_called_once_with(
        processing_run_dir,
        processed_run_dir
    )


def test_main_does_not_archive_processing_run_when_import_fails(tmp_path: Path):
    app_dir = tmp_path / "app"
    config_path = tmp_path / "config" / "imports.toml"
    run_id = "123"
    processing_run_dir = config_path.parent / "processing" / run_id
    processed_run_dir = config_path.parent / "processed" / run_id

    import_config = ImportConfig(
        "test",
        "test.xlsx",
        "sheet1",
        "schema1",
        "table1"
    )
    import_configs = [import_config]

    import_tasks = [
        ImportTask(
            import_config,
            tmp_path / "source_test.xlsx",
            processing_run_dir / "001_test.xlsx"
        )
    ]

    conn_mock = MagicMock()
    sql_columns = [[]]

    with (
        patch("src.import_excel.read_imports", return_value=import_configs),
        patch("src.import_excel.build_manual_import_tasks"),
        patch(
            "src.import_excel.get_processing_run_dir",
            return_value=processing_run_dir
        ),
        patch(
            "src.import_excel.build_scheduled_import_tasks",
            return_value=import_tasks
        ),
        patch("src.import_excel.validate_import_sources"),
        patch("src.import_excel.create_processing_run_dir"),
        patch("src.import_excel.move_source_files"),
        patch("src.import_excel.validate_excel_sources"),
        patch("src.import_excel.os.getenv", return_value="connection"),
        patch("src.import_excel.connect") as connect_mock,
        patch("src.import_excel.validate_target_tables"),
        patch("src.import_excel.get_sql_meta_columns", return_value=sql_columns),
        patch("src.import_excel.validate_target_columns"),
        patch("src.import_excel.validate_excel_data"),
        patch("src.import_excel.import_all_data", side_effect=RuntimeError("Import all data error")),
        patch("src.import_excel.get_processed_run_dir", return_value=processed_run_dir) as processed_dir_mock,
        patch("src.import_excel.archive_processing_run") as archive_processing_mock
    ):
        connect_mock.return_value.__enter__.return_value = conn_mock
        with pytest.raises(RuntimeError, match="Import all data error"):
            main(app_dir, config_path, True, run_id)

    processed_dir_mock.assert_not_called()
    archive_processing_mock.assert_not_called()