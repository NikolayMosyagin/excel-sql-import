import pytest

from src.sql_utils import quote_identifier


@pytest.mark.parametrize(
    "source_value, target_value",
    [
        ("dbo", "[dbo]"),
        ("ReportData", "[ReportData]"),
        ("a]b", "[a]]b]"),
    ]
)
def test_quote_identifier(source_value: str, target_value: str):
    assert quote_identifier(source_value) == target_value