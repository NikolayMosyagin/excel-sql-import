from datetime import datetime

import pandas as pd
import pytest

from src.value_validators import validate_datetime_values
from src.sql_meta_column import SqlMetaColumn


@pytest.fixture
def sql_column() -> SqlMetaColumn:
    return SqlMetaColumn("datetime_column", "datetime", 0, 0, 0, False)


@pytest.mark.parametrize(
    "invalid_value",
    [
        "2026-08-21 00:00:00",
        [datetime(2026, 8, 21)],
        100000,
        1000.0
    ]
)
def test_validate_datetime_reject_invalid_type(sql_column: SqlMetaColumn, invalid_value: object):
    with pytest.raises(ValueError):
        validate_datetime_values(sql_column, pd.Series([invalid_value]))


@pytest.mark.parametrize(
    "invalid_value",
    [
        datetime(1752, 12, 31),
        datetime(1, 1, 1),
        datetime(9999, 12, 31, 23, 59, 59, 999000),
        datetime(9999, 12, 31, 23, 59, 59, 999999)
    ]
)
def test_validate_datetime_reject_outside_range(sql_column: SqlMetaColumn, invalid_value: datetime):
    with pytest.raises(ValueError):
        validate_datetime_values(sql_column, pd.Series([invalid_value]))


@pytest.mark.parametrize(
    "invalid_value",
    [
        datetime(2026, 8, 21, 11, 16, 59, 1000),
        datetime(2026, 8, 21, 11, 17, 59, 2000),
        datetime(2026, 8, 21, 11, 18, 59, 4000),
    ]
)
def test_validate_datetime_reject_invalid_microsecond(sql_column: SqlMetaColumn, invalid_value: datetime):
    with pytest.raises(ValueError):
        validate_datetime_values(sql_column, pd.Series([invalid_value]))


@pytest.mark.parametrize(
    "valid_value",
    [
        datetime(1753, 1, 1),
        datetime(2026, 8, 21, 11, 16, 59),
        datetime(2026, 8, 21, 11, 16, 50, 123000),
        datetime(2026, 8, 21, 11, 16, 10, 997000),
        pd.Timestamp(9999, 12, 31, 23, 59, 59, 997000)
    ]
)
def test_validate_datetime_accept_valid_value(sql_column: SqlMetaColumn, valid_value: datetime):
    validate_datetime_values(sql_column, pd.Series([valid_value]))