from pathlib import Path

import pandas as pd
import pytest

from src.import_config import ImportConfig
from src.import_task import ImportTask
from src.import_source_validators import validate_import_sources, validate_excel_sources


@pytest.fixture
def import_configs() -> list[ImportConfig]:
    return [
        ImportConfig('test1', 'test1.xlsx', 'sheet1', 'schema1', 'table1'),
        ImportConfig('test2', 'test2.xlsx', 'sheet1', 'schema1', 'table2')
    ]

@pytest.fixture
def import_tasks(tmp_path: Path, import_configs: list[ImportConfig]) -> list[ImportTask]:
    return [
        ImportTask(import_config, tmp_path / f"source_{import_config.file}", tmp_path / f"working_{import_config.file}")
        for import_config in import_configs
    ]


@pytest.fixture
def data_frame() -> pd.DataFrame:
    return pd.DataFrame({"Name": ["Name1", "Name2"], "Age": [10, 20]})


def test_validate_import_sources_reject_missing_file(import_tasks: list[ImportTask]):
    with pytest.raises(FileNotFoundError, match="Source file not found:"):
        validate_import_sources(import_tasks)


def test_validate_import_sources_reject_directory(tmp_path: Path):
    import_config = ImportConfig('test1', 'test1', 'sheet1', 'schema1', 'table1')
    import_tasks = [ImportTask(import_config, tmp_path / import_config.file, tmp_path / import_config.file)]
    import_tasks[0].source_file.mkdir()
    with pytest.raises(IsADirectoryError, match="Expected a file, but found a directory:"):
        validate_import_sources(import_tasks)


def test_validate_import_sources_reject_missing_file_in_later_config(import_tasks: list[ImportTask]):
    import_tasks[0].source_file.write_text("", encoding="utf-8")
    with pytest.raises(FileNotFoundError, match="Source file not found: "):
        validate_import_sources(import_tasks)


def test_validate_import_sources_accept_valid_files(import_tasks: list[ImportTask]):
    import_tasks[0].source_file.write_text("", encoding="utf-8")
    import_tasks[1].source_file.write_text("", encoding="utf-8")
    validate_import_sources(import_tasks)


def test_validate_excel_sources_reject_missing_sheet(tmp_path: Path, data_frame: pd.DataFrame):
    import_config = ImportConfig("test", "test.xlsx", "sheet1", "schema1", "table1")
    import_tasks = [ImportTask(import_config, tmp_path / import_config.file, tmp_path / import_config.file)]
    data_frame.to_excel(import_tasks[0].working_file, sheet_name="otherSheet", index=False)
    with pytest.raises(ValueError, match="doesn't contain sheet"):
        validate_excel_sources(import_tasks)


def test_validate_excel_sources_reject_empty_sheet(tmp_path: Path):
    import_config = ImportConfig("test", "test.xlsx", "sheet1", "schema1", "table1")
    import_tasks = [ImportTask(import_config, tmp_path / import_config.file, tmp_path / import_config.file)]
    pd.DataFrame({}).to_excel(import_tasks[0].working_file, sheet_name=import_config.sheet, index=False)
    with pytest.raises(ValueError, match="is empty"):
        validate_excel_sources(import_tasks)


def test_validate_excel_sources_reject_empty_sheet_in_later_config(
    import_tasks: list[ImportTask],
    data_frame: pd.DataFrame
):
    data_frame.to_excel(import_tasks[0].working_file, sheet_name=import_tasks[0].config.sheet, index=False)
    pd.DataFrame({}).to_excel(import_tasks[1].working_file, sheet_name=import_tasks[1].config.sheet, index=False)
    with pytest.raises(ValueError, match="is empty"):
        validate_excel_sources(import_tasks)


def test_validate_excel_sources_accept_valid_files(
    import_tasks: list[ImportTask],
    data_frame: pd.DataFrame
):
    for import_task in import_tasks:
        data_frame.to_excel(import_task.working_file, sheet_name=import_task.config.sheet, index=False)

    validate_excel_sources(import_tasks)