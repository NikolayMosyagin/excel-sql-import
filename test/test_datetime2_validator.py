from datetime import datetime

import pandas as pd
import pytest

from src.value_validators import validate_datetime2_values
from src.sql_meta_column import SqlMetaColumn


@pytest.mark.parametrize(
    "invalid_value",
    [
        "2026-08-21 00:00:00",
        [datetime(2026, 8, 21)],
        100000,
        1000.0
    ]
)
def test_validate_datetime2_reject_invalid_type(invalid_value: object):
    sql_column = SqlMetaColumn("datetime2_column", "datetime2", 0, 0, 2, False)
    with pytest.raises(ValueError):
        validate_datetime2_values(sql_column, pd.Series([invalid_value]))


@pytest.mark.parametrize(
    "scale_value, time_value",
    [
        (0, datetime(2026, 8, 21, 12, 3, 20, 20)),
        (0, datetime(2026, 8, 21, 12, 3, 20, 100000)),
        (1, datetime(2026, 8, 21, 12, 3, 20, 120000)),
        (1, datetime(2026, 8, 21, 12, 3, 20, 100010)),
        (2, datetime(2026, 8, 21, 12, 3, 20, 123000)),
        (2, datetime(2026, 8, 21, 12, 3, 49, 120001)),
        (3, datetime(2026, 8, 21, 12, 11, 4, 123400)),
        (3, datetime(2026, 8, 21, 12, 11, 4, 123020)),
        (4, datetime(2026, 8, 21, 12, 11, 4, 123420)),
        (4, datetime(2026, 8, 21, 12, 11, 4, 123401)),
        (5, datetime(2026, 8, 21, 12, 11, 4, 123411)),
    ]
)
def test_validate_datetime2_reject_excess_fractional_precision(scale_value: int, time_value: datetime):
    sql_column = SqlMetaColumn("datetime2_column", "datetime2", 0, 0, scale_value, False)
    with pytest.raises(ValueError):
        validate_datetime2_values(sql_column, pd.Series([time_value]))


@pytest.mark.parametrize(
    "scale_value, time_value",
    [
        (0, datetime(2026, 8, 21, 12, 3, 20)),
        (1, datetime(2026, 8, 21, 12, 3, 20, 100000)),
        (1, datetime(2026, 8, 21, 12, 3, 20, 900000)),
        (2, datetime(2026, 8, 21, 12, 3, 20, 110000)),
        (2, datetime(2026, 8, 21, 12, 3, 49, 990000)),
        (3, datetime(2026, 8, 21, 12, 11, 4, 111000)),
        (3, datetime(2026, 8, 21, 12, 11, 4, 999000)),
        (4, datetime(2026, 8, 21, 12, 11, 4, 123400)),
        (4, datetime(2026, 8, 21, 12, 11, 4, 999900)),
        (5, datetime(2026, 8, 21, 12, 11, 4, 123410)),
        (5, datetime(2026, 8, 21, 12, 11, 4, 999990)),
        (6, datetime(2026, 8, 21, 12, 11, 4, 999999)),
        (6, pd.Timestamp(year=2026, month=8, day=21, hour=12, minute=11, second=4)),
        (7, pd.Timestamp(year=2026, month=8, day=21, hour=12, minute=11, second=4, microsecond=999999)),
    ]
)
def test_validate_datetime2_accept_valid_fractional_precision(scale_value: int, time_value: datetime):
    sql_column = SqlMetaColumn("datetime2_column", "datetime2", 0, 0, scale_value, False)
    validate_datetime2_values(sql_column, pd.Series([time_value]))