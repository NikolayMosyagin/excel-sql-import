from pathlib import Path

import pytest

from src.excel_utils import get_excel_engine

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