import pandas as pd
import pytest

from src.value_validators import validate_float_values
from src.sql_meta_column import SqlMetaColumn


@pytest.mark.parametrize(
    "invalid_value",
    ["10", "10.0", [10.5], (11.5, ), False]
)
def test_validate_float_reject_unsupported_type(invalid_value: object):
    sql_column = SqlMetaColumn("float_column", "float", 0, 0, 0, False)
    with pytest.raises(ValueError):
        validate_float_values(sql_column, pd.Series([invalid_value]))


@pytest.mark.parametrize(
    "invalid_value",
    [float("inf"), float("-inf"), float("nan")]
)
def test_validate_float_reject_non_finite_value(invalid_value: float):
    sql_column = SqlMetaColumn("float_column", "real", 0, 0, 0, False)
    with pytest.raises(ValueError):
        validate_float_values(sql_column, pd.Series([invalid_value]))


@pytest.mark.parametrize(
    "sql_type, precision, invalid_value",
    [
        ("real", 0, 5.0E+38),
        ("real", 0, -1.0E+39),
        ("real", 0, 1.0E-39),
        ("float", 24, 5.0E+38),
        ("float", 24, -5.0E+38),
        ("float", 24, 1.0E-39),
        ("float", 25, 1.0E-309),
    ]
)
def test_validate_float_reject_outside_range(sql_type: str, precision: int, invalid_value: float):
    sql_column = SqlMetaColumn(f"{sql_type}_column", sql_type, 0, precision, 0, False)
    with pytest.raises(ValueError):
        validate_float_values(sql_column, pd.Series([invalid_value]))


@pytest.mark.parametrize(
    "sql_type, precision, valid_value",
    [
        ("real", 0, 0),
        ("real", 0, 1),
        ("real", 0, 1.18E-38),
        ("real", 0, 3.40E+38),
        ("float", 24, 0),
        ("float", 24, 1),
        ("float", 24, 1.18E-38),
        ("float", 24, 3.40E+38),
        ("float", 25, 0),
        ("float", 25, 1),
        ("float", 25, 2.23E-308),
        ("float", 25, 1.79E+308),
        ("float", 53, 123.456)
    ]
)
def test_validate_float_accept_valid_value(sql_type: str, precision: int, valid_value: float):
    sql_column = SqlMetaColumn(f"{sql_type}_column", sql_type, 0, precision, 0, False)
    validate_float_values(sql_column, pd.Series([valid_value]))