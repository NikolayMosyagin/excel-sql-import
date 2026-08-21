from datetime import datetime

import pandas as pd
import pytest

from src.import_excel import validate_date_values
from src.sql_meta_column import SqlMetaColumn


@pytest.fixture
def sql_column() -> SqlMetaColumn:
    return SqlMetaColumn("date_column", "date", 0, 0, 0, False)


@pytest.mark.parametrize(
    "invalid_value",
    [
        "21.08.2026",
        "2026-08-21 00:00:00",
        [datetime(2026, 8, 21)],
        100000,
    ]
)
def test_validate_date_reject_invalid_type(sql_column: SqlMetaColumn, invalid_value: object):
    with pytest.raises(ValueError):
        validate_date_values(sql_column, pd.Series([invalid_value]))


@pytest.mark.parametrize(
    "invalid_value",
    [
        datetime(2026, 8, 21, 1, 0, 0, 0),
        datetime(2026, 8, 21, 0, 1, 0, 0),
        datetime(2026, 8, 21, 0, 0, 1, 0),
        datetime(2026, 8, 21, 0, 0, 0, 1),
    ]
)
def test_validate_date_reject_date_with_time(sql_column: SqlMetaColumn, invalid_value: datetime):
    with pytest.raises(ValueError):
        validate_date_values(sql_column, pd.Series([invalid_value]))


@pytest.mark.parametrize(
    "valid_value",
    [
        datetime(2026, 8, 21),
        datetime(1, 1, 1),
        datetime(9999, 12, 31),
        pd.Timestamp(year=2026, month=8, day=21),
        pd.Timestamp(year=1, month=1, day=1),
        pd.Timestamp(year=9999, month=12, day=31)
    ]
)
def test_validate_date_accept_valid_value(sql_column: SqlMetaColumn, valid_value: datetime):
    validate_date_values(sql_column, pd.Series([valid_value]))
