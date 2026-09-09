from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.import_config import ImportConfig, ImportMode
from src.sql_meta_column import SqlMetaColumn
from src.excel_data_validators import (
    validate_excel_columns,
    validate_upsert_key_columns,
    validate_date_format_columns,
    validate_target_columns, 
    validate_excel_data,
)


@pytest.fixture
def sql_columns() -> list[SqlMetaColumn]:
    return [
        SqlMetaColumn("name1", "int", 0, 0, 0, False),
        SqlMetaColumn("name2", "int", 0, 0, 0, False)
    ]


@pytest.fixture
def import_config() -> ImportConfig:
    return ImportConfig("config1", "test.xlsx", "sheet1", "schema1", "table1")


@pytest.fixture
def config_path(tmp_path: Path) -> Path:
    return tmp_path / "config" / "imports.toml"


def test_validate_excel_columns_reject_missing_column():
    df = pd.DataFrame({
        "name1": [1, 2]
    })
    errors = validate_excel_columns(
        df, 
        {"name1", "name2"}, 
        "schema1.table1"
    )
    assert len(errors) == 1
    assert "Excel source is missing columns required by" in errors[0]
    assert "name2" in errors[0]


def test_validate_excel_columns_reject_extra_column():
    df = pd.DataFrame({
        "name1": [1, 2],
        "name2": [1, 2],
        "name3": [1, 3]
    })
    errors = validate_excel_columns(
        df,
        {"name1", "name2"},
        "schema1.table1"
    )
    assert len(errors) == 1
    assert "Excel source contains columns not present in" in errors[0]
    assert "name3" in errors[0]


def test_validate_excel_columns_reject_extra_and_missing_column():
    df = pd.DataFrame({
        "name1": [1, 2],
        "name_2": [1, 2],
    })
    errors = validate_excel_columns(
        df,
        {"name1", "name2"},
        "schema1.table1"
    )

    assert len(errors) == 2
    assert "Excel source is missing columns required" in errors[0]
    assert "name2" in errors[0]
    assert "Excel source contains columns not present" in errors[1]
    assert "name_2" in errors[1]


def test_validate_excel_columns_reject_duplicate_column_names():
    df = pd.DataFrame({
        "name1": [1, 2],
        "name2": [1, 10]
    })
    df = df.rename(columns={"name2": "name1"})

    errors = validate_excel_columns(
        df,
        {"name1", "name2"},
        "schema1.table1"
    )

    assert len(errors) == 2
    assert "Excel source contains duplicate column names after applying column mapping:" in errors[0]
    assert "name1" in errors[0]
    assert "Excel source is missing columns required" in errors[1]
    assert "name2" in errors[1]


def test_validate_excel_columns_accept_valid_data():
    df = pd.DataFrame({
        "name2": [1, 2],
        "name1": [1, 2],
    })
    errors = validate_excel_columns(
        df,
        {"name1", "name2"},
        "schema1.table1"
    )
    assert len(errors) == 0


def test_validate_date_format_columns_accepts_valid_date_column():
    excel_columns = {"Column1", "ColumnDate"}
    sql_meta_columns = [
        SqlMetaColumn("Column1", "int", 0, 0, 0, False),
        SqlMetaColumn("ColumnDate", "date", 0, 0, 0, False)
    ]
    date_formats = {
        "ColumnDate": "%d.%m.%Y"
    }
    errors = validate_date_format_columns(
        excel_columns,
        sql_meta_columns,
        date_formats
    )
    assert len(errors) == 0


def test_validate_date_format_columns_rejects_missing_column():
    excel_columns = {"Column1", "ColumnDate"}
    sql_meta_columns = [
        SqlMetaColumn("Column1", "int", 0, 0, 0, False),
        SqlMetaColumn("ColumnDate", "date", 0, 0, 0, False)
    ]
    date_formats = {
        "ColumnDatE": "%d.%m.%Y"
    }
    errors = validate_date_format_columns(
        excel_columns,
        sql_meta_columns,
        date_formats
    )
    assert len(errors) == 1
    assert "Columns from 'date_formats' are not present in Excel" in errors[0]


@pytest.mark.parametrize(
    "sql_column_type",
    ["int", "nvarchar", "decimal"]
)
def test_validate_date_format_columns_rejects_invalid_type(sql_column_type: str):
    excel_columns = {"Column1", "ColumnDate"}
    sql_meta_columns = [
        SqlMetaColumn("Column1", "int", 0, 0, 0, False),
        SqlMetaColumn("ColumnDate", sql_column_type, 0, 0, 0, False)
    ]
    date_formats = {
        "ColumnDate": "%d.%m.%Y"
    }
    errors = validate_date_format_columns(
        excel_columns,
        sql_meta_columns,
        date_formats
    )
    assert len(errors) == 1
    assert "date_formats' can only be used for SQL date/time columns, but got:" in errors[0]
    assert sql_column_type in errors[0]
    assert "ColumnDate" in errors[0]


@pytest.mark.parametrize(
    "sql_column_type",
    ["date", "datetime", "datetime2", "smalldatetime"]
)
def test_validate_date_format_columns_accepts_valid_date_type(sql_column_type: str):
    excel_columns = {"Column1", "ColumnDate"}
    sql_meta_columns = [
        SqlMetaColumn("Column1", "int", 0, 0, 0, False),
        SqlMetaColumn("ColumnDate", sql_column_type, 0, 0, 0, False)
    ]
    date_formats = {
        "ColumnDate": "%d.%m.%Y"
    }
    errors = validate_date_format_columns(
        excel_columns,
        sql_meta_columns,
        date_formats
    )
    assert len(errors) == 0


def test_validate_date_format_columns_multiple_errors():
    excel_columns = {"Column1", "ColumnDate"}
    sql_meta_columns = [
        SqlMetaColumn("Column1", "int", 0, 0, 0, False),
        SqlMetaColumn("ColumnDate", "date", 0, 0, 0, False)
    ]
    date_formats = {
        "ColumnDatE": "%d.%m.%Y",
        "Column1": "%d.%m.%Y"
    }
    errors = validate_date_format_columns(
        excel_columns,
        sql_meta_columns,
        date_formats
    )
    assert len(errors) == 2
    assert "Columns from 'date_formats' are not present in Excel" in errors[0]
    assert "ColumnDatE" in errors[0]
    assert "'date_formats' can only be used for SQL date/time columns, but got:" in errors[1]
    assert "Column1 (int)" in errors[1]

def test_validate_upsert_key_columns_accept_with_one_key():
    import_config = ImportConfig("config1", "test.xlsx", "sheet1", "schema1", "table1", ImportMode.UPSERT, ("name1",))
    errors = validate_upsert_key_columns(
        import_config,
        {"name1", "name2"}
    )
    assert len(errors) == 0


def test_validate_upsert_key_columns_ignores_non_upsert_mode():
    import_config = ImportConfig("config1", "test.xlsx", "sheet1", "schema1", "table1")
    errors = validate_upsert_key_columns(
        import_config,
        {"name1", "name2"}
    )
    assert len(errors) == 0


def test_validate_upsert_key_columns_accept_with_multiple_keys():
    import_config = ImportConfig("config1", "test.xlsx", "sheet1", "schema1", "table1", ImportMode.UPSERT, ("name1", "name2"))
    errors = validate_upsert_key_columns(
        import_config,
        {"name1", "name2"}
    )
    assert len(errors) == 0


def test_validate_upsert_key_columns_reject_missing_key_column():
    import_config = ImportConfig("config1", "test.xlsx", "sheet1", "schema1", "table1", ImportMode.UPSERT, ("name1", "test"))
    errors = validate_upsert_key_columns(
        import_config,
        {"name1", "name2"}
    )
    assert len(errors) == 1
    assert "Key columns are not present in target table 'schema1.table1': test." == errors[0]


def test_validate_upsert_key_columns_reject_missing_key_columns():
    import_config = ImportConfig("config1", "test.xlsx", "sheet1", "schema1", "table1", ImportMode.UPSERT, ("name1", "test", "test2"))
    errors = validate_upsert_key_columns(
        import_config,
        {"name1", "name2"}
    )
    assert len(errors) == 1
    assert "Key columns are not present in target table 'schema1.table1': test, test2." == errors[0]


def test_validate_target_columns_accepts_when_all_validators_return_no_errors(
    config_path: Path,
    sql_columns: list[SqlMetaColumn],
    import_config: ImportConfig
):
    df = pd.DataFrame({
        "name1": [1, 2],
        "name2": [10, 20]
    })
    with (
        patch("src.excel_data_validators.read_excel_dataframe") as read_excel_mock,
        patch("src.excel_data_validators.validate_excel_columns") as excel_columns_mock,
        patch("src.excel_data_validators.validate_date_format_columns") as date_formats_mock,
        patch("src.excel_data_validators.validate_upsert_key_columns") as upsert_key_mock,
    ):
        read_excel_mock.return_value = df
        excel_columns_mock.return_value = []
        date_formats_mock.return_value = []
        upsert_key_mock.return_value = []
        validate_target_columns(config_path, sql_columns, import_config)

    read_excel_mock.assert_called_once_with(
        config_path,
        import_config.sheet,
        import_config.column_mapping,
        nrows=0
    )
    excel_columns_mock.assert_called_once_with(
        df,
        {column.name for column in sql_columns},
        f"{import_config.schema}.{import_config.table}"
    )
    date_formats_mock.assert_called_once_with(
        set(df.columns),
        sql_columns,
        import_config.date_formats
    )
    upsert_key_mock.assert_called_once_with(
        import_config,
        {column.name for column in sql_columns}
    )


def test_validate_target_columns_aggregates_errors_from_all_validators(
    config_path: Path,
    sql_columns: list[SqlMetaColumn],
    import_config: ImportConfig
):
    df = pd.DataFrame({
        "name1": [1, 2],
        "name_2": [10, 20]
    })
    with (
        patch("src.excel_data_validators.read_excel_dataframe") as read_excel_mock,
        patch("src.excel_data_validators.validate_excel_columns") as excel_columns_mock,
        patch("src.excel_data_validators.validate_date_format_columns") as date_formats_mock,
        patch("src.excel_data_validators.validate_upsert_key_columns") as upsert_key_mock,
    ):
        read_excel_mock.return_value = df
        excel_columns_mock.return_value = ["Excel columns error"]
        date_formats_mock.return_value = ["Date formats error"]
        upsert_key_mock.return_value = ["Upsert key error"]

        with pytest.raises(ValueError) as exc_info:
            validate_target_columns(config_path, sql_columns, import_config)
    
    read_excel_mock.assert_called_once_with(
        config_path,
        import_config.sheet,
        import_config.column_mapping,
        nrows=0
    )
    excel_columns_mock.assert_called_once_with(
        df,
        {column.name for column in sql_columns},
        f"{import_config.schema}.{import_config.table}"
    )
    date_formats_mock.assert_called_once_with(
        set(df.columns),
        sql_columns,
        import_config.date_formats
    )
    upsert_key_mock.assert_called_once_with(
        import_config,
        {column.name for column in sql_columns}
    )
    error_message = str(exc_info.value)
    assert "Import 'config1':" in error_message
    assert "Excel columns error" in error_message
    assert "Date formats error" in error_message
    assert "Upsert key error" in error_message
    

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
        validate_excel_data(file_path, sql_columns, import_config)


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

    validate_excel_data(file_path, sql_columns, import_config)


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
        validate_excel_data(file_path, sql_columns, import_config)


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
    validate_excel_data(file_path, sql_columns, import_config)


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
        validate_excel_data(file_path, sql_columns, import_config)


def test_validate_excel_data_reject_null_in_upsert_key_column(tmp_path: Path):
    import_config = ImportConfig("config1", "test.xlsx", "sheet1", "schema1", "table1", ImportMode.UPSERT, ("name1",))
    sql_columns = [
        SqlMetaColumn("name1", "int", 0, 0, 0, True),
        SqlMetaColumn("name2", "int", 0, 0, 0, False),
    ]
    data = {
        "name1": [1, None, 3],
        "name2": [10, 20, 30]
    }
    file_path = tmp_path / import_config.file
    pd.DataFrame(data).to_excel(file_path, sheet_name=import_config.sheet, index=False)
    with pytest.raises(ValueError, match="Key column 'name1' cannot contain NULL values for UPSERT, "):
        validate_excel_data(file_path, sql_columns, import_config)


def test_validate_excel_data_reject_null_in_later_upsert_key_column(tmp_path: Path):
    import_config = ImportConfig("config1", "test.xlsx", "sheet1", "schema1", "table1", ImportMode.UPSERT, ("name1", "name2"))
    sql_columns = [
        SqlMetaColumn("name1", "int", 0, 0, 0, True),
        SqlMetaColumn("name2", "int", 0, 0, 0, True),
    ]
    data = {
        "name1": [1, 20, 3],
        "name2": [10, 20, None]
    }
    file_path = tmp_path / import_config.file
    pd.DataFrame(data).to_excel(file_path, sheet_name=import_config.sheet, index=False)
    with pytest.raises(ValueError, match="Key column 'name2' cannot contain NULL values for UPSERT, "):
        validate_excel_data(file_path, sql_columns, import_config)


def test_validate_excel_data_accept_valid_upsert_keys(tmp_path: Path):
    import_config = ImportConfig("config1", "test.xlsx", "sheet1", "schema1", "table1", ImportMode.UPSERT, ("name1", "name2"))
    sql_columns = [
        SqlMetaColumn("name1", "int", 0, 0, 0, True),
        SqlMetaColumn("name2", "int", 0, 0, 0, True),
    ]
    data = {
        "name1": [1, 20, 3],
        "name2": [10, 20, 30]
    }
    file_path = tmp_path / import_config.file
    pd.DataFrame(data).to_excel(file_path, sheet_name=import_config.sheet, index=False)
    validate_excel_data(file_path, sql_columns, import_config)


def test_validate_excel_data_reject_duplicate_single_key(tmp_path: Path):
    import_config = ImportConfig("config1", "test.xlsx", "sheet1", "schema1", "table1", ImportMode.UPSERT, ("name1",))
    sql_columns = [
        SqlMetaColumn("name1", "int", 0, 0, 0, True),
        SqlMetaColumn("name2", "int", 0, 0, 0, True),
    ]
    data = {
        "name1": [1, 20, 1],
        "name2": [10, 20, 30]
    }
    file_path = tmp_path / import_config.file
    pd.DataFrame(data).to_excel(file_path, sheet_name=import_config.sheet, index=False)
    with pytest.raises(ValueError, match="Excel contains duplicate values for UPSERT key columns 'name1'") as exc_info:
        validate_excel_data(file_path, sql_columns, import_config)

    assert "Duplicate rows: 2, 4." in str(exc_info.value)


def test_validate_excel_data_reject_duplicate_composite_key(tmp_path: Path):
    import_config = ImportConfig("config1", "test.xlsx", "sheet1", "schema1", "table1", ImportMode.UPSERT, ("name1", "name2"))
    sql_columns = [
        SqlMetaColumn("name1", "int", 0, 0, 0, True),
        SqlMetaColumn("name2", "int", 0, 0, 0, True),
        SqlMetaColumn("name3", "int", 0, 0, 0, True),
    ]
    data = {
        "name1": [1, 2, 1],
        "name2": [10, 10, 10],
        "name3": [100, 200, 300]
    }
    file_path = tmp_path / import_config.file
    pd.DataFrame(data).to_excel(file_path, sheet_name=import_config.sheet, index=False)
    with pytest.raises(ValueError, match="Excel contains duplicate values for UPSERT key columns 'name1, name2'"):
        validate_excel_data(file_path, sql_columns, import_config)


def test_validate_excel_data_accept_duplicate_values_in_individual_key_columns(tmp_path: Path):
    import_config = ImportConfig("config1", "test.xlsx", "sheet1", "schema1", "table1", ImportMode.UPSERT, ("name1", "name2"))
    sql_columns = [
        SqlMetaColumn("name1", "int", 0, 0, 0, True),
        SqlMetaColumn("name2", "int", 0, 0, 0, True),
    ]
    data = {
        "name1": [1, 1, 2],
        "name2": [10, 20, 10]
    }
    file_path = tmp_path / import_config.file
    pd.DataFrame(data).to_excel(file_path, sheet_name=import_config.sheet, index=False)
    validate_excel_data(file_path, sql_columns, import_config)