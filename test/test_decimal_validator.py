import pytest
import pandas as pd

from src.sql_meta_column import SqlMetaColumn
from src.import_excel import validate_decimal_values


@pytest.mark.parametrize(
    "invalid_value",
    [False, "10", "10.0", (10.0, ), [10.2]]
)
def test_validate_decimal_reject_unsupported_type(invalid_value: object):
    sql_column = SqlMetaColumn("decimal_column", "decimal", 0, 0, 0, False)
    with pytest.raises(ValueError):
        validate_decimal_values(sql_column, pd.Series([invalid_value]))


@pytest.mark.parametrize(
    "invalid_value",
    [float("-inf"), float("inf"), float("nan")]
)
def test_validate_decimal_reject_non_finite_value(invalid_value: float):
    sql_column = SqlMetaColumn("decimal_column", "decimal", 0, 0, 0, False)
    with pytest.raises(ValueError):
        validate_decimal_values(sql_column, pd.Series([invalid_value]))


@pytest.mark.parametrize(
    "precision, scale, invalid_value",
    [
        (4, 2, 0.234),
        (6, 1, 0.23),
        (5, 5, 0.000001)
    ]
)
def test_validate_decimal_reject_excess_fractional_digits(precision: int, scale: int, invalid_value: float):
    sql_column = SqlMetaColumn("decimal_column", "decimal", 0, precision, scale, False)
    with pytest.raises(ValueError):
        validate_decimal_values(sql_column, pd.Series([invalid_value]))


@pytest.mark.parametrize(
    "precision, scale, invalid_value",
    [
        (4, 2, 123.23),
        (6, 3, -1234.1),
        (4, 1, 1200.0),
        (1, 1, 1.0)
    ]
)
def test_validate_decimal_reject_excess_integer_digits(precision: int, scale: int, invalid_value: float):
    sql_column = SqlMetaColumn("decimal_column", "decimal", 0, precision, scale, False)
    with pytest.raises(ValueError):
        validate_decimal_values(sql_column, pd.Series([invalid_value]))


@pytest.mark.parametrize(
    "precision, scale, valid_value",
    [
        (4, 2, 12.23),
        (6, 3, -123.1),
        (4, 2, 0.23),
        (6, 1, 0.9),
        (7, 1, 123456),
        (5, 1, 1200.0),
        (5, 5, 0.00123),
        (1, 1, 0.0)
    ]
)
def test_validate_decimal_accept_valid_value(precision: int, scale: int, valid_value: float):
    sql_column = SqlMetaColumn("decimal_column", "decimal", 0, precision, scale, False)
    validate_decimal_values(sql_column, pd.Series([valid_value]))
