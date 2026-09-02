from pathlib import Path

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