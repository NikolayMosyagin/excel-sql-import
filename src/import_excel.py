from pathlib import Path
import tomllib
import pandas as pd

from src.import_config import ImportConfig


def read_imports(root: Path) -> list[ImportConfig]:
    imports_path = root / 'config' / 'imports.toml'
    IMPORTS_KEY = 'imports'
    if not imports_path.exists():
        raise FileNotFoundError(f"Configuration file not found: '{imports_path}'.")
    
    with open(imports_path, "rb") as imports_file:
        data = tomllib.load(imports_file)

    if IMPORTS_KEY not in data:
        raise ValueError(f"Required configuration key '{IMPORTS_KEY}' is missing.")

    imports = data[IMPORTS_KEY]
    if not isinstance(imports, list):
        raise TypeError(f"Configuration key '{IMPORTS_KEY}' must be a list.")
    if not imports:
        raise ValueError(f"Configuration key '{IMPORTS_KEY}' cannot be empty.")
    
    import_configs: list[ImportConfig] = []
    for import_data in imports:
        if not isinstance(import_data, dict):
            raise TypeError(f"Import configuration must be a dictionary.")
        try:
            import_configs.append(ImportConfig(**import_data))
        except (TypeError, ValueError) as original_error:
            raise ValueError(
                f"Invalid import configuration '{import_data.get('name', 'unknown')}':\n"
                f"{original_error}"
            ) from original_error
    return import_configs


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


root_path = Path(__file__).resolve().parents[1]
import_configs = read_imports(root_path)
validate_import_sources(root_path, import_configs)
validate_excel_sources(root_path, import_configs)

for import_config in import_configs:
    source_file = root_path / import_config.file
    df = pd.read_excel(source_file, sheet_name=import_config.sheet, engine='openpyxl')
    rows, columns = df.shape
    print(f"""Import: {import_config.name}
Source: {import_config.file}
Sheet: {import_config.sheet}
Target: {import_config.schema}.{import_config.table}
Rows: {rows}
Columns: {columns}"""
    )

