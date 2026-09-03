from collections.abc import Mapping
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
