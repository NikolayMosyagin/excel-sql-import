from pathlib import Path

from src.import_config import ImportConfig
from src.import_task import ImportTask
from src.import_task_builder import (
    get_unique_source_files,
    build_manual_import_tasks,
    build_scheduled_import_tasks
)


def test_get_unique_source_files(tmp_path: Path):
    import_configs = [
        ImportConfig("test1", "../data/test.xlsx", "sheet1", "schema1", "table1"),
        ImportConfig("test2", "data/test.xlsx", "sheet2", "schema2", "table2"),
        ImportConfig("test3", "test/../../data/test.xlsx", "sheet3", "schema3", "table3")
    ]

    result = get_unique_source_files(tmp_path, import_configs)

    assert result == [
        (tmp_path.parent / "data" / "test.xlsx").resolve(),
        (tmp_path / "data" / "test.xlsx").resolve()
    ]


def test_build_manual_import_tasks(tmp_path: Path):
    import_configs = [
        ImportConfig("test1", "data/test.xlsx", "sheet1", "schema1", "table1"),
        ImportConfig("test2", "test/test.xlsx", "sheet1", "schema2", "table2"),
    ]

    result = build_manual_import_tasks(tmp_path, import_configs)

    assert len(result) == 2
    assert result == [
        ImportTask(import_configs[0], tmp_path / import_configs[0].file, tmp_path / import_configs[0].file),
        ImportTask(import_configs[1], tmp_path / import_configs[1].file, tmp_path / import_configs[1].file)
    ]


def test_build_scheduled_import_tasks_one_source_file(tmp_path: Path):
    import_configs = [
        ImportConfig("test1", "data/file.xlsx", "sheet1", "schema1", "table1"),
        ImportConfig("test2", "data/file.xlsx", "sheet2", "schema1", "table2")
    ]
    processing_dir = tmp_path / "processing" / "run"
    result = build_scheduled_import_tasks(tmp_path, import_configs, processing_dir)

    assert len(result) == 2
    assert result[0].source_file == tmp_path / result[0].config.file
    assert result[0].working_file == result[1].working_file
    assert result[0].working_file == processing_dir / "001_file.xlsx"


def test_build_scheduled_import_tasks_two_different_source_file_with_same_name(tmp_path: Path):
    import_configs = [
        ImportConfig("test1", "data/file.xlsx", "sheet1", "schema1", "table1"),
        ImportConfig("test2", "data_other/file.xlsx", "sheet2", "schema1", "table2")
    ]
    processing_dir = tmp_path / "processing" / "run"
    result = build_scheduled_import_tasks(tmp_path, import_configs, processing_dir)

    assert len(result) == 2
    assert result[0].working_file != result[1].working_file
    assert result[0].source_file == tmp_path / result[0].config.file
    assert result[1].source_file == tmp_path / result[1].config.file
    assert result[0].working_file == processing_dir / "001_file.xlsx"
    assert result[1].working_file == processing_dir / "002_file.xlsx"