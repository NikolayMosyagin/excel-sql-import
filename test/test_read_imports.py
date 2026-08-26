from pathlib import Path

import pytest

from src.config_loader import read_imports
from src.import_config import ImportMode


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
    assert import_config.mode == ImportMode.REPLACE


def test_read_imports_return_valid_import_config_with_mode(tmp_path: Path):
    import_text = """
[[imports]]
name = 'e2e_test'
file = 'data/e2e_import_test.xlsx'
sheet = 'RollbackFailure'
schema = 'dbo'
table = 'ImportE2ETest'
mode = 'append'"""
    create_imports_file(tmp_path, import_text)

    import_configs = read_imports(tmp_path)
    assert len(import_configs) == 1
    import_config = import_configs[0]
    assert import_config.name == "e2e_test"
    assert import_config.file == "data/e2e_import_test.xlsx"
    assert import_config.sheet == "RollbackFailure"
    assert import_config.schema == "dbo"
    assert import_config.table == "ImportE2ETest"
    assert import_config.mode == ImportMode.APPEND


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
    [ "name", "file", "sheet", "schema", "table", "mode"]
)
def test_read_imports_reject_invalid_import_config_value(tmp_path: Path, invalid_key: str):
    imports = {
        "name": "e2e_test",
        "file": "data/e2e_import_test.xlsx",
        "sheet": "RollbackFailure",
        "schema": "dbo",
        "table": "ImportE2ETest",
        "mode": "append"
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


def test_read_imports_reject_unknown_mode(tmp_path: Path):
    import_text = """
[[imports]]
name = 'e2e_test'
file = 'data/e2e_import_test.xlsx'
sheet = 'RollbackFailure'
schema = 'dbo'
table = 'ImportE2ETest'
mode = 'update'
"""
    create_imports_file(tmp_path, import_text)

    with pytest.raises(ValueError, match="Invalid import configuration"):
        read_imports(tmp_path)


@pytest.mark.parametrize(
    "key_columns_text, expected_key_columns",
    [
        ("key_columns = [\"ID\"]", ("ID",)),
        ("key_columns = [\"ReportDate\", \"Department\"]", ("ReportDate", "Department"))
    ]
)
def test_read_imports_return_upsert_config_with_key_columns(
    tmp_path: Path,
    key_columns_text: str,
    expected_key_columns: tuple[str, ...]
):
    import_text = """
[[imports]]
name = 'e2e_test'
file = 'data/e2e_import_test.xlsx'
sheet = 'RollbackFailure'
schema = 'dbo'
table = 'ImportE2ETest'
mode = 'upsert'""" + "\n" + key_columns_text
    create_imports_file(tmp_path, import_text)

    import_configs = read_imports(tmp_path)
    assert len(import_configs) == 1
    assert import_configs[0].mode == ImportMode.UPSERT
    assert import_configs[0].key_columns == expected_key_columns


def test_read_imports_reject_upsert_without_key_columns(tmp_path: Path):
    import_text = """
[[imports]]
name = 'e2e_test'
file = 'data/e2e_import_test.xlsx'
sheet = 'RollbackFailure'
schema = 'dbo'
table = 'ImportE2ETest'
mode = 'upsert'"""

    create_imports_file(tmp_path, import_text)
    with pytest.raises(ValueError, match="must not be empty for mode 'upsert'"):
        read_imports(tmp_path)


def test_read_imports_reject_upsert_with_empty_key_columns(tmp_path: Path):
    import_text = """
[[imports]]
name = 'e2e_test'
file = 'data/e2e_import_test.xlsx'
sheet = 'RollbackFailure'
schema = 'dbo'
table = 'ImportE2ETest'
mode = 'upsert'
key_columns = []"""
    create_imports_file(tmp_path, import_text)
    with pytest.raises(ValueError, match="The attribute 'key_columns' must not be empty for mode 'upsert'"):
        read_imports(tmp_path)


@pytest.mark.parametrize(
    "mode_value",
    ["replace", "append"]
)
def test_read_imports_reject_key_columns_for_non_upsert_mode(tmp_path: Path, mode_value: str):
    import_text = """
[[imports]]
name = 'e2e_test'
file = 'data/e2e_import_test.xlsx'
sheet = 'RollbackFailure'
schema = 'dbo'
table = 'ImportE2ETest'""" + "\n" + f"mode = '{mode_value}'\n" + "key_columns = [\"ID\"]"
    create_imports_file(tmp_path, import_text)
    with pytest.raises(ValueError, match=f"The attribute 'key_columns' must be empty for mode '{mode_value}'"):
        read_imports(tmp_path)


@pytest.mark.parametrize(
    "key_columns_value",
    ["'Id'", 123]
)
def test_read_imports_reject_non_list_key_columns(tmp_path: Path, key_columns_value: object):
    import_text = """
[[imports]]
name = 'e2e_test'
file = 'data/e2e_import_test.xlsx'
sheet = 'RollbackFailure'
schema = 'dbo'
table = 'ImportE2ETest'
mode = 'upsert'""" + "\n" + f"key_columns = {key_columns_value}"
    
    create_imports_file(tmp_path, import_text)
    with pytest.raises(ValueError, match="Configuration key 'key_columns' must be a list"):
        read_imports(tmp_path)


def test_read_imports_reject_invalid_key_column_type(tmp_path: Path):
    import_text = """
[[imports]]
name = 'e2e_test'
file = 'data/e2e_import_test.xlsx'
sheet = 'RollbackFailure'
schema = 'dbo'
table = 'ImportE2ETest'
mode = 'upsert'
key_columns = ["ID", 123]"""
    create_imports_file(tmp_path, import_text)
    with pytest.raises(ValueError, match="All elements of 'key_columns' must be strings."):
        read_imports(tmp_path)


