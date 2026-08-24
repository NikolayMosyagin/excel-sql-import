from pathlib import Path

import pandas as pd

from src.import_config import ImportConfig


def validate_import_sources(root: Path, import_configs: list[ImportConfig]) -> None:
    for import_config in import_configs:
        source_file = root / import_config.file
        if not source_file.exists():
            raise FileNotFoundError(f"Source file not found: '{source_file}'.")
    
        if source_file.is_dir():
            raise IsADirectoryError(f"Expected a file, but found a directory: '{source_file}'.")


def validate_excel_sources(root: Path, import_configs: list[ImportConfig]) -> None:
    for import_config in import_configs:
        source_file = root / import_config.file
        with pd.ExcelFile(source_file, engine='openpyxl') as excel_file:
            if import_config.sheet not in excel_file.sheet_names:
                raise ValueError(f"Source file '{source_file}' doesn't contain sheet '{import_config.sheet}'.")
            df = excel_file.parse(sheet_name=import_config.sheet, nrows=1)
        
        if df.empty:
            raise ValueError(f"Sheet '{import_config.sheet}' in source file '{source_file}' is empty.")