from datetime import datetime

import pandas as pd
import pytest

from src.value_validators import validate_smalldatetime_values
from src.sql_meta_column import SqlMetaColumn


@pytest.fixture
def sql_column() -> SqlMetaColumn:
    return SqlMetaColumn("smalldatetime_column", "smalldatetime", 0, 0, 0, False)


@pytest.mark.parametrize(
    "invalid_value",
    [
        "21.08.2026",
        "2026-08-21 00:00:00",
        [datetime(2026, 8, 21)],
        100000,
    ]
)
def test_validate_smalldatetime_reject_invalid_type(sql_column: SqlMetaColumn, invalid_value: object):
    with pytest.raises(ValueError):
        validate_smalldatetime_values(sql_column, pd.Series([invalid_value]))


@pytest.mark.parametrize(
    "invalid_value",
    [
        datetime(1899, 12, 31, 23, 59),
        datetime(1899, 12, 31),
        datetime(1700, 1, 1),
        datetime(1, 1, 1),
        pd.Timestamp(year=2079, month=6, day=7),
        pd.Timestamp(year=9999, month=12, day=31),
        pd.Timestamp(year=2100, month=7, day=20)
    ]
)
def test_validate_smalldatetime_reject_outside_range(sql_column: SqlMetaColumn, invalid_value: datetime):
    with pytest.raises(ValueError):
        validate_smalldatetime_values(sql_column, pd.Series([invalid_value]))


@pytest.mark.parametrize(
    "invalid_value",
    [
        datetime(1900, 1, 1, 20, 30, 1),
        datetime(2026, 8, 21, 1, 13, 0, 1000),
        pd.Timestamp(year=2026, month=8, day=21, hour=1, minute=13, second=1),
        pd.Timestamp(year=2026, month=8, day=21, hour=1, minute=13, microsecond=1000)
    ]
)
def test_validate_smalldatetime_reject_nonzero_seconds_or_microseconds(sql_column: SqlMetaColumn, invalid_value: datetime):
    with pytest.raises(ValueError):
        validate_smalldatetime_values(sql_column, pd.Series([invalid_value]))


@pytest.mark.parametrize(
    "valid_value",
    [
        datetime(1900, 1, 1, 0, 0),
        datetime(2079, 6, 6, 23, 59),
        datetime(2026, 8, 21, 1, 17),
        pd.Timestamp(1994, 5, 31)
    ]
)
def test_validate_smalldatetime_accept_valid_value(sql_column: SqlMetaColumn, valid_value: datetime):
    validate_smalldatetime_values(sql_column, pd.Series([valid_value]))