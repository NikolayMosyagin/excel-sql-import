from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest

from src.excel_utils import (
    get_excel_engine, 
    apply_date_formats, 
    prepare_excel_dataframe
)

@pytest.mark.parametrize(
    "file_path, expected_engine",
    [
        (Path("data/test.xlsx"), "openpyxl"),
        (Path("test2.xls"), "xlrd"),
        (Path("tt.XlsX"), "openpyxl"),
        (Path("t_.XLS"), "xlrd")
    ]
)
def test_get_excel_engine_accepts_supported_extension(file_path: Path, expected_engine: str):
    assert get_excel_engine(file_path) == expected_engine


@pytest.mark.parametrize(
    "file_path",
    [
        Path("test.csv"),
        Path("data/test")
    ]
)
def test_get_excel_engine_rejects_unsupported_extension(file_path: Path):
    with pytest.raises(ValueError, match="Unsupported Excel file extension"):
        get_excel_engine(file_path)


def test_apply_date_formats_rejects_invalid_type():
    df = pd.DataFrame({
        "Date": ["21.12.2024", "21.05.2000"],
        "Date1": ["10.02.1999", 52]
    })
    date_formats = {
        "Date": "%d.%m.%Y",
        "Date1": "%d.%m.%Y"
    }
    with pytest.raises(ValueError, match=r"Column 'Date1', row 3:.*expected a date string matching format"):
        apply_date_formats(df, date_formats)


def test_apply_date_formats_rejects_invalid_format():
    df = pd.DataFrame({
        "Date": ["21/12/2025", "24/12/2025"]
    })
    date_formats = {
        "Date": "%d.%m.%Y"
    }
    with pytest.raises(ValueError, match=r"does not match date format '%d\.%m\.%Y'"):
        apply_date_formats(df, date_formats)


def test_apply_date_formats_accepts_correct_values():
    df = pd.DataFrame({
        "Date": ["21.12.2000", pd.NA, None, datetime(2025, 12, 22)]
    })
    date_formats = {
        "Date": "%d.%m.%Y"
    }
    df = apply_date_formats(df, date_formats)
    assert df["Date"].to_list() == [datetime(2000, 12, 21), pd.NA, None, datetime(2025, 12, 22)]
    assert df["Date"].dtype == object


def test_apply_date_formats_accepts_different_formats():
    df = pd.DataFrame({
        "Date": ["21.12.2000"],
        "DateTime": ["2025-10-16 14:30:00"]
    })
    date_formats = {
        "Date": "%d.%m.%Y",
        "DateTime": "%Y-%m-%d %H:%M:%S"
    }
    df = apply_date_formats(df, date_formats)
    assert df.at[0, "Date"] == datetime(2000, 12, 21)
    assert df.at[0, "DateTime"] == datetime(2025, 10, 16, 14, 30)


def test_prepare_excel_dataframe_applies_mapping_before_date_formats(tmp_path: Path):
    source_file = tmp_path / "test.xlsx"
    df = pd.DataFrame({
        "Имя_1": ["10.12.2026"]
    })
    df.to_excel(source_file, sheet_name="Sheet1", index=False)
    column_mapping = {
        "Имя_1": "Name1"
    }
    date_formats = {
        "Name1": "%d.%m.%Y"
    }

    new_df = prepare_excel_dataframe(
        source_file,
        "Sheet1",
        column_mapping,
        date_formats
    )
    assert new_df.at[0, "Name1"] == datetime(2026, 12, 10)