from pathlib import Path

import pytest

from src.config_loader import read_imports


def create_imports_file(root: Path, content: str) -> None:
    config_dir = root / "config"
    config_dir.mkdir()

    imports_path = config_dir / "imports.toml"
    imports_path.write_text(content, encoding="utf-8")


def test_read_imports_reject_missing_file(tmp_path: Path):
    with pytest.raises(FileNotFoundError, match="Configuration file not found:"):
        read_imports(tmp_path)


def test_read_imports_reject_missing_imports_key(tmp_path: Path):
    create_imports_file(tmp_path, "")

    with pytest.raises(ValueError, match="Required configuration key 'imports' is missing."):
        read_imports(tmp_path)


@pytest.mark.parametrize(
    "config_text",
    ['imports="name"', '[imports]\nname = "Ivan"']
)
def test_read_imports_reject_non_list_imports(tmp_path: Path, config_text: str):
    create_imports_file(tmp_path, config_text)

    with pytest.raises(TypeError, match="Configuration key 'imports' must be a list."):
        read_imports(tmp_path)


def test_read_imports_reject_empty_imports(tmp_path: Path):
    create_imports_file(tmp_path, "imports = []")

    with pytest.raises(ValueError, match="Configuration key 'imports' cannot be empty."):
        read_imports(tmp_path)


def test_read_imports_reject_non_dict_import_item(tmp_path: Path):
    create_imports_file(tmp_path, "imports = [42, true]")

    with pytest.raises(TypeError, match="Import configuration must be a dictionary."):
        read_imports(tmp_path)


def test_read_imports_return_valid_import_config(tmp_path: Path):
    import_text = """
[[imports]]
name = 'e2e_test'
file = 'data/e2e_import_test.xlsx'
sheet = 'RollbackFailure'
schema = 'dbo'
table = 'ImportE2ETest'"""
    create_imports_file(tmp_path, import_text)

    import_configs = read_imports(tmp_path)
    assert len(import_configs) == 1
    import_config = import_configs[0]
    assert import_config.name == "e2e_test"
    assert import_config.file == "data/e2e_import_test.xlsx"
    assert import_config.sheet == "RollbackFailure"
    assert import_config.schema == "dbo"
    assert import_config.table == "ImportE2ETest"


def test_read_imports_return_multiple_import_configs(tmp_path: Path):
    import_text = """
[[imports]]
name = "validate_int"
file = "data/test_int_validator.xlsx"
sheet = "test_int"
schema = "dbo"
table = "test_int"

[[imports]]
name = "report_data"
file = "data/sample_report_data.xlsx"
sheet = "ReportData"
schema = "dbo"
table = "ReportData"
"""
    create_imports_file(tmp_path, import_text)
    import_configs = read_imports(tmp_path)
    assert len(import_configs) == 2
    assert import_configs[0].name == "validate_int"
    assert import_configs[1].name == "report_data"


@pytest.mark.parametrize(
    "invalid_key",
    [ "name", "file", "sheet", "schema", "table"]
)
def test_read_imports_reject_invalid_import_config_value(tmp_path: Path, invalid_key: str):
    imports = {
        "name": "e2e_test",
        "file": "data/e2e_import_test.xlsx",
        "sheet": "RollbackFailure",
        "schema": "dbo",
        "table": "ImportE2ETest"
    }
    imports[invalid_key] = 2
    import_text = "[[imports]]\n" + "\n".join(f"{key} = {value!r}" for key, value in imports.items())
    create_imports_file(tmp_path, import_text)

    with pytest.raises(ValueError, match="Invalid import configuration"):
        read_imports(tmp_path)


@pytest.mark.parametrize(
    "missing_key",
    ["name", "file", "sheet", "schema", "table"]
)
def test_read_imports_reject_missing_required_field(tmp_path: Path, missing_key: str):
    imports = {
        "name": "e2e_test",
        "file": "data/e2e_import_test.xlsx",
        "sheet": "RollbackFailure",
        "schema": "dbo",
        "table": "ImportE2ETest"
    }
    del imports[missing_key]
    import_text = "[[imports]]\n" + "\n".join(f"{key} = {value!r}" for key, value in imports.items())
    create_imports_file(tmp_path, import_text)
    with pytest.raises(ValueError, match="Invalid import configuration"):
        read_imports(tmp_path)


def test_read_imports_reject_extra_import_config_field(tmp_path: Path):
    import_text = """
[[imports]]
name = 'e2e_test'
file = 'data/e2e_import_test.xlsx'
sheet = 'RollbackFailure'
schema = 'dbo'
table = 'ImportE2ETest'
extraField = 'aaaa'"""
    create_imports_file(tmp_path, import_text)
    with pytest.raises(ValueError, match="Invalid import configuration"):
        read_imports(tmp_path)


@pytest.mark.parametrize(
    "empty_value",
    ["", "   "]
)
def test_read_imports_reject_blank_import_config_value(tmp_path: Path, empty_value: str):
    imports = {
        "name": "e2e_test",
        "file": "data/e2e_import_test.xlsx",
        "sheet": "RollbackFailure",
        "schema": "dbo",
        "table": "ImportE2ETest"
    }
    imports["file"] = empty_value
    import_text = "[[imports]]\n" + "\n".join(f"{key} = {value!r}" for key, value in imports.items())
    create_imports_file(tmp_path, import_text)
    with pytest.raises(ValueError, match="Invalid import configuration"):
        read_imports(tmp_path)