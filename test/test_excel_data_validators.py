from pathlib import Path

import pandas as pd
import pytest

from src.import_config import ImportConfig
from src.sql_meta_column import SqlMetaColumn
from src.excel_data_validators import validate_target_columns, validate_excel_data


@pytest.fixture
def sql_columns() -> list[SqlMetaColumn]:
    return [
        SqlMetaColumn("name1", "int", 0, 0, 0, False),
        SqlMetaColumn("name2", "int", 0, 0, 0, False)
    ]


@pytest.fixture
def import_config() -> ImportConfig:
    return ImportConfig("config1", "test.xlsx", "sheet1", "schema1", "table1")


def test_validate_target_columns_reject_missing_column(
    tmp_path: Path,
    sql_columns: list[SqlMetaColumn],
    import_config: ImportConfig
):
    data = {
        "name1": [1, 2],
    }
    file_path = tmp_path / import_config.file
    pd.DataFrame(data).to_excel(file_path, sheet_name=import_config.sheet, index=False)
    with pytest.raises(ValueError, match="Excel source is missing columns required"):
        validate_target_columns(tmp_path, sql_columns, import_config)


def test_validate_target_columns_reject_extra_column(
    tmp_path: Path,
    sql_columns: list[SqlMetaColumn],
    import_config: ImportConfig
):
    data = {
        "name1": [1, 2],
        "name2": [1, 2],
        "name3": [1, 3]
    }
    file_path = tmp_path / import_config.file
    pd.DataFrame(data).to_excel(file_path, sheet_name=import_config.sheet, index=False)
    with pytest.raises(ValueError, match="Excel source contains columns not present in"):
        validate_target_columns(tmp_path, sql_columns, import_config)


def test_validate_target_columns_reject_extra_and_missing_column(
    tmp_path: Path,
    sql_columns: list[SqlMetaColumn],
    import_config: ImportConfig
):
    data = {
        "name1": [1, 2],
        "name_2": [1, 2],
    }
    file_path = tmp_path / import_config.file
    pd.DataFrame(data).to_excel(file_path, sheet_name=import_config.sheet, index=False)
    with pytest.raises(ValueError) as exc_info:
        validate_target_columns(tmp_path, sql_columns, import_config)

    error_message = str(exc_info.value)

    assert "Excel source is missing columns required" in error_message
    assert "Excel source contains columns not present" in error_message


def test_validate_target_columns_accept_valid_data(
    tmp_path: Path,
    sql_columns: list[SqlMetaColumn],
    import_config: ImportConfig
):
    data = {
        "name2": [1, 2],
        "name1": [1, 2],
    }
    file_path = tmp_path / import_config.file
    pd.DataFrame(data).to_excel(file_path, sheet_name=import_config.sheet, index=False)
    validate_target_columns(tmp_path, sql_columns, import_config)


def test_validate_excel_data_reject_null_in_non_nullable_column(
    tmp_path: Path,
    import_config: ImportConfig
):
    sql_columns = [
        SqlMetaColumn("name1", "int", 0, 0, 0, False)
    ]
    data = { "name1": [None, 2] }
    file_path = tmp_path / import_config.file
    pd.DataFrame(data).to_excel(file_path, sheet_name=import_config.sheet, index=False)

    with pytest.raises(ValueError, match="does not allow NULL values, but Excel contains"):
        validate_excel_data(tmp_path, sql_columns, import_config)


def test_validate_excel_data_accept_null_in_nullable_column(
    tmp_path: Path,
    import_config: ImportConfig
):
    sql_columns = [
        SqlMetaColumn("name1", "int", 0, 0, 0, True)
    ]
    data = { "name1": [None, 2] }
    file_path = tmp_path / import_config.file
    pd.DataFrame(data).to_excel(file_path, sheet_name=import_config.sheet, index=False)

    validate_excel_data(tmp_path, sql_columns, import_config)


def test_validate_excel_data_reject_unsupported_sql_type(
    tmp_path: Path,
    import_config: ImportConfig
):
    sql_columns = [
        SqlMetaColumn("name1", "unknown_type", 0, 0, 0, True)
    ]
    data = {"name1": [None, 2]}
    file_path = tmp_path / import_config.file
    pd.DataFrame(data).to_excel(file_path, sheet_name=import_config.sheet, index=False)
    with pytest.raises(ValueError, match="is not supported."):
        validate_excel_data(tmp_path, sql_columns, import_config)


def test_validate_excel_data_accept_valid_data(
    tmp_path: Path,
    import_config: ImportConfig
):
    sql_columns = [
        SqlMetaColumn("name1", "int", 0, 0, 0, True),
        SqlMetaColumn("name2", "int", 0, 0, 0, True)
    ]
    data = {
        "name1": [None, 2, 3],
        "name2": [2, None, None]
    }
    file_path = tmp_path / import_config.file
    pd.DataFrame(data).to_excel(file_path, sheet_name=import_config.sheet, index=False)
    validate_excel_data(tmp_path, sql_columns, import_config)


def test_validate_excel_data_reject_null_in_non_nullable_later_column(
    tmp_path: Path,
    import_config: ImportConfig
):
    sql_columns = [
        SqlMetaColumn("name1", "int", 0, 0, 0, True),
        SqlMetaColumn("name2", "int", 0, 0, 0, False)
    ]
    data = {
        "name1": [None, 2, 3],
        "name2": [2, 3, None]
    }
    file_path = tmp_path / import_config.file
    pd.DataFrame(data).to_excel(file_path, sheet_name=import_config.sheet, index=False)
    with pytest.raises(ValueError, match="empty values."):
        validate_excel_data(tmp_path, sql_columns, import_config)