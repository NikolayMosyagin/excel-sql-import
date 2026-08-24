from pathlib import Path

import pandas as pd
import pytest

from src.import_config import ImportConfig
from src.import_source_validators import validate_import_sources, validate_excel_sources


@pytest.fixture
def import_configs() -> list[ImportConfig]:
    return [
        ImportConfig('test1', 'test1.xlsx', 'sheet1', 'schema1', 'table1'),
        ImportConfig('test2', 'test2.xlsx', 'sheet1', 'schema1', 'table2')
    ]


@pytest.fixture
def data_frame() -> pd.DataFrame:
    return pd.DataFrame({"Name": ["Name1", "Name2"], "Age": [10, 20]})


def test_validate_import_sources_reject_missing_file(tmp_path: Path, import_configs: list[ImportConfig]):
    with pytest.raises(FileNotFoundError, match="Source file not found:"):
        validate_import_sources(tmp_path, import_configs)


def test_validate_import_sources_reject_directory(tmp_path: Path):
    import_config = ImportConfig('test1', 'test1', 'sheet1', 'schema1', 'table1')
    data_dir = tmp_path / import_config.file
    data_dir.mkdir()
    with pytest.raises(IsADirectoryError, match="Expected a file, but found a directory:"):
        validate_import_sources(tmp_path, [import_config])


def test_validate_import_sources_reject_missing_file_in_later_config(tmp_path: Path, import_configs: list[ImportConfig]):
    file_path = tmp_path / import_configs[0].file
    file_path.write_text("", encoding="utf-8")
    with pytest.raises(FileNotFoundError, match="Source file not found: "):
        validate_import_sources(tmp_path, import_configs)


def test_validate_import_sources_accept_valid_files(tmp_path: Path, import_configs: list[ImportConfig]):
    file1 = tmp_path / import_configs[0].file
    file2 = tmp_path / import_configs[1].file
    file1.write_text("", encoding="utf-8")
    file2.write_text("", encoding="utf-8")
    validate_import_sources(tmp_path, import_configs)


def test_validate_excel_sources_reject_missing_sheet(tmp_path: Path, data_frame: pd.DataFrame):
    import_config = ImportConfig("test", "test.xlsx", "sheet1", "schema1", "table1")
    file_path = tmp_path / import_config.file
    data_frame.to_excel(file_path, sheet_name="otherSheet", index=False)
    with pytest.raises(ValueError, match="doesn't contain sheet"):
        validate_excel_sources(tmp_path, [import_config])


def test_validate_excel_sources_reject_empty_sheet(tmp_path: Path):
    import_config = ImportConfig("test", "test.xlsx", "sheet1", "schema1", "table1")
    file_path = tmp_path / import_config.file
    pd.DataFrame({}).to_excel(file_path, sheet_name="sheet1", index=False)
    with pytest.raises(ValueError, match="is empty"):
        validate_excel_sources(tmp_path, [import_config])


def test_validate_excel_sources_reject_empty_sheet_in_later_config(
    tmp_path: Path, 
    import_configs: list[ImportConfig],
    data_frame: pd.DataFrame
):
    file_path1 = tmp_path / import_configs[0].file
    data_frame.to_excel(file_path1, sheet_name=import_configs[0].sheet, index=False)
    file_path2 = tmp_path / import_configs[1].file
    pd.DataFrame({}).to_excel(file_path2, sheet_name=import_configs[1].sheet, index=False)
    with pytest.raises(ValueError, match="is empty"):
        validate_excel_sources(tmp_path, import_configs)


def test_validate_excel_sources_accept_valid_files(
    tmp_path: Path,
    import_configs: list[ImportConfig],
    data_frame: pd.DataFrame
):
    for config in import_configs:
        file_path = tmp_path / config.file
        data_frame.to_excel(file_path, sheet_name=config.sheet, index=False)
    validate_excel_sources(tmp_path, import_configs)