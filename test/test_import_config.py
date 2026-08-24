import pytest

from src.import_config import ImportConfig, ImportMode


def test_import_config_accept_valid_values():
    import_config = ImportConfig("config1", "file1.xlsx", "sheet1", "schema1", "table1")
    assert import_config.name == "config1"
    assert import_config.file == "file1.xlsx"
    assert import_config.sheet == "sheet1"
    assert import_config.schema == "schema1"
    assert import_config.table == "table1"
    assert import_config.mode == ImportMode.REPLACE


@pytest.mark.parametrize(
    "invalid_pos",
    [ 0, 1, 2, 3, 4]
)
def test_import_config_reject_non_string_attribute(invalid_pos: int):
    source = ["config1", "file1.xlsx", "sheet1", "schema1", "table1"]
    source[invalid_pos] = 2
    with pytest.raises(TypeError):
        ImportConfig(*source)


@pytest.mark.parametrize(
    "empty_pos",
    [0, 1, 2, 3, 4]
)
def test_import_config_reject_blank_attribute(empty_pos: int):
    source = ["config1", "file1.xlsx", "sheet1", "schema1", "table1"]
    source[empty_pos] = "    "
    with pytest.raises(ValueError):
        ImportConfig(*source)

    source[empty_pos] = ""
    with pytest.raises(ValueError):
        ImportConfig(*source)


@pytest.mark.parametrize(
    "import_mode",
    [ImportMode.REPLACE, ImportMode.APPEND]
)
def test_import_config_accept_valid_mode(import_mode: ImportMode):
    import_config = ImportConfig("config1", "file1.xlsx", "sheet1", "schema1", "table1", import_mode)
    assert import_config.mode == import_mode


@pytest.mark.parametrize(
    "invalid_mode",
    ["APPEND", 1, [ImportMode.APPEND]]
)
def test_import_config_reject_invalid_mode(invalid_mode: object):
    with pytest.raises(TypeError):
        ImportConfig("config1", "file1.xlsx", "sheet1", "schema1", "table1", invalid_mode)