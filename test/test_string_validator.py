import pandas as pd
import pytest

from src.import_excel import validate_string_values
from src.sql_meta_column import SqlMetaColumn


@pytest.mark.parametrize(
    "invalid_value",
    [100, False, -100.0, ("123", ), ["123"]]
)
def test_validate_string_reject_unsupported_type(invalid_value: object):
    sql_column = SqlMetaColumn("string_column", "nvarchar", 100, 0, 0, False)
    with pytest.raises(ValueError):
        validate_string_values(sql_column, pd.Series([invalid_value]))


@pytest.mark.parametrize(
    "sql_type, max_length, invalid_value",
    [
        ("char", 10, "1" * 11),
        ("varchar", 5, "abcdef"),
        ("nchar", 20, "a" * 11),
        ("nvarchar", 4, "abc"),
    ]
)
def test_validate_string_reject_invalid_length(sql_type: str, max_length: int, invalid_value: str):
    sql_column = SqlMetaColumn(f"{sql_type}_column", sql_type, max_length, 0, 0, False)
    with pytest.raises(ValueError):
        validate_string_values(sql_column, pd.Series([invalid_value]))


@pytest.mark.parametrize(
    "sql_type, valid_value",
    [
        ("varchar", "a" * 100),
        ("nvarchar", "b" * 100)
    ]
)
def test_validate_string_accept_unlimited_length(sql_type: str, valid_value: str):
    sql_column = SqlMetaColumn(f"{sql_type}_column", sql_type, -1, 0, 0, False)
    validate_string_values(sql_column, pd.Series([valid_value]))


@pytest.mark.parametrize(
    "sql_type, max_length, valid_value",
    [
        ("char", 10, "1" * 10),
        ("char", 10, ""),
        ("varchar", 5, "abcde"),
        ("varchar", 5, ""),
        ("nchar", 20, "a" * 10),
        ("nchar", 20, ""),
        ("nvarchar", 4, "ab"),
        ("nvarchar", 4, ""),
    ]
)
def test_validate_string_accept_valid_value(sql_type: str, max_length: int, valid_value: str):
    sql_column = SqlMetaColumn(f"{sql_type}_column", sql_type, max_length, 0, 0, False)
    validate_string_values(sql_column, pd.Series([valid_value]))