from pathlib import Path
import tomllib

from src.import_config import ImportConfig, ImportMode


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
            if (source_mode := import_data.get("mode")) is not None:
                import_data["mode"] = ImportMode(source_mode)

            if (source_key_columns := import_data.get("key_columns")) is not None:
                if not isinstance(source_key_columns, list):
                    raise TypeError("Configuration key 'key_columns' must be a list.")
                import_data["key_columns"] = tuple(source_key_columns)

            import_configs.append(ImportConfig(**import_data))
        except (TypeError, ValueError) as original_error:
            raise ValueError(
                f"Invalid import configuration '{import_data.get('name', 'unknown')}':\n"
                f"{original_error}"
            ) from original_error
    return import_configs