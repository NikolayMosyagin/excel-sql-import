import pytest
import pandas as pd
from src.sql_meta_column import SqlMetaColumn
from src.import_excel import validate_integer_values


@pytest.mark.parametrize(
    "sql_type, min_value, max_value",
    [
        ("tinyint", 0, 255),
        ("smallint", -32768, 32767),
        ("int", -2147483648, 2147483647),
        ("bigint", -9223372036854775808, 9223372036854775807)
    ]
)
def test_validate_integer_correct_values(sql_type: str, min_value: int, max_value: int):
    sql_column = SqlMetaColumn(f"{sql_type}_column", sql_type, 0, 0, 0, False)
    validate_integer_values(sql_column, pd.Series([min_value, max_value, 0, (min_value + max_value) // 2]))


@pytest.mark.parametrize(
    "sql_type, invalid_value",
    [
        ("tinyint", 256),
        ("smallint", 32768),
        ("int", 2147483648),
        ("bigint", 9223372036854775808)
    ]
)
def test_validate_integer_reject_overflow_value(sql_type: str, invalid_value: int):
    sql_column = SqlMetaColumn(f"{sql_type}_column", sql_type, 0, 0, 0, False)
    with pytest.raises(ValueError):
        validate_integer_values(sql_column, pd.Series([invalid_value]))


@pytest.mark.parametrize(
    "sql_type, invalid_value",
    [
        ("tinyint", -1),
        ("smallint", -32769),
        ("int", -2147483649),
        ("bigint", -9223372036854775809)
    ]
)
def test_validate_integer_reject_underflow_value(sql_type: str, invalid_value: int):
    sql_column = SqlMetaColumn(f"{sql_type}_column", sql_type, 0, 0, 0, False)
    with pytest.raises(ValueError):
        validate_integer_values(sql_column, pd.Series([invalid_value]))