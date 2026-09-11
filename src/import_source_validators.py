import pandas as pd

from src.import_task import ImportTask
from src.excel_utils import get_excel_engine


def validate_import_sources(import_tasks: list[ImportTask]) -> None:
    for import_task in import_tasks:
        source_file = import_task.source_file
        if not source_file.exists():
            raise FileNotFoundError(f"Source file not found: '{source_file}'.")
    
        if source_file.is_dir():
            raise IsADirectoryError(f"Expected a file, but found a directory: '{source_file}'.")


def validate_excel_sources(import_tasks: list[ImportTask]) -> None:
    for import_task in import_tasks:
        working_file = import_task.working_file
        sheet = import_task.config.sheet
        with pd.ExcelFile(working_file, engine=get_excel_engine(working_file)) as excel_file:
            if sheet not in excel_file.sheet_names:
                raise ValueError(f"Source file '{working_file}' doesn't contain sheet '{sheet}'.")
            df = excel_file.parse(sheet_name=sheet, nrows=1)
        
        if df.empty:
            raise ValueError(f"Sheet '{sheet}' in source file '{working_file}' is empty.")