from collections.abc import Mapping
from datetime import datetime
from pathlib import Path

import pandas as pd

ENGINE_BY_EXTENSION = {
    ".xls": "xlrd",
    ".xlsx": "openpyxl"
}

def get_excel_engine(file_path: Path) -> str:
    ext = file_path.suffix.lower()
    engine = ENGINE_BY_EXTENSION.get(ext)
    if engine is None:
        raise ValueError(f"Unsupported Excel file extension '{ext}'. "
                         f"Supported extensions: {", ".join(ENGINE_BY_EXTENSION)}.")

    return engine


def read_excel_dataframe(
    source_file: Path, 
    sheet: str,
    column_mapping: Mapping[str, str],
    nrows: int | None = None
) -> pd.DataFrame:
    df = pd.read_excel(
        source_file, 
        sheet_name=sheet, 
        engine=get_excel_engine(source_file),
        nrows=nrows
    )
    df = df.rename(columns=column_mapping)
    return df


def apply_date_formats(
    df: pd.DataFrame,
    date_formats: Mapping[str, str]
) -> pd.DataFrame:
    for column_name, date_format in date_formats.items():
        converted_values = []

        for index, value in df[column_name].items():
            if pd.isna(value) or isinstance(value, datetime):
                converted_values.append(value)
                continue

            if not isinstance(value, str):
                raise ValueError(
                    f"Column '{column_name}', row {index + 2}: "
                    f"expected a date string matching format '{date_format}', "
                    f"but got '{value}' of type '{type(value).__name__}'."
                )

            try:
                converted_values.append(
                    datetime.strptime(value, date_format)
                )
            except ValueError as original_error:
                raise ValueError(
                    f"Column '{column_name}', row {index + 2}: "
                    f"value '{value}' does not match date format '{date_format}'."
                ) from original_error
        df[column_name] = pd.Series(
            converted_values,
            index=df.index,
            dtype=object
        )

    return df


def prepare_excel_dataframe(
    source_file: Path,
    sheet: str,
    column_mapping: Mapping[str, str],
    date_formats: Mapping[str, str]
) -> pd.DataFrame:
    
    df = read_excel_dataframe(
        source_file,
        sheet,
        column_mapping
    )

    df = apply_date_formats(
        df,
        date_formats
    )
    return df