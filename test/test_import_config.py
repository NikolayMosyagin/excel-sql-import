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
    assert import_config.key_columns == ()


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
    "invalid_mode",
    ["APPEND", 1, [ImportMode.APPEND]]
)
def test_import_config_reject_invalid_mode(invalid_mode: object):
    with pytest.raises(TypeError):
        ImportConfig("config1", "file1.xlsx", "sheet1", "schema1", "table1", invalid_mode)


@pytest.mark.parametrize(
    "invalid_key_columns",
    ["Id", 1, ["Id"]]
)
def test_import_config_reject_invalid_key_columns_type(invalid_key_columns: object):
    with pytest.raises(TypeError, match="The attribute 'key_columns' must be of type 'tuple'."):
        ImportConfig("config1", "file1.xlsx", "sheet1", "schema1", "table1", key_columns=invalid_key_columns)


@pytest.mark.parametrize(
    "mode",
    [ImportMode.REPLACE, ImportMode.APPEND]
)
def test_import_config_reject_non_empty_key_columns_for_replace_or_append(mode: ImportMode):
    with pytest.raises(ValueError, match="The attribute 'key_columns' must be empty for mode"):
        ImportConfig("config1", "file1.xlsx", "sheet1", "schema1", "table1", mode, ("Id",))


def test_import_config_reject_empty_key_columns_for_upsert():
    with pytest.raises(ValueError, match="The attribute 'key_columns' must not be empty for mode "):
        ImportConfig("config1", "file1.xlsx", "sheet1", "schema1", "table1", ImportMode.UPSERT, ())


@pytest.mark.parametrize(
    "key_columns",
    [("Id", None), ("Id", 123), ("Id", ["123"])]
)
def test_import_config_reject_invalid_key_columns_element_type(key_columns: tuple[object, ...]):
    with pytest.raises(TypeError, match="All elements of 'key_columns' must be strings."):
        ImportConfig("config1", "file1.xlsx", "sheet1", "schema1", "table1", ImportMode.UPSERT, key_columns)


@pytest.mark.parametrize(
    "key_columns",
    [("", "ID"), ("ID", "   ")]
)
def test_import_config_reject_blank_key_column(key_columns: tuple[str, ...]):
    with pytest.raises(ValueError, match="The attribute 'key_columns' must contain only non-empty strings."):
        ImportConfig("config1", "file1.xlsx", "sheet1", "schema1", "table1", ImportMode.UPSERT, key_columns)


def test_import_config_reject_duplicate_key_columns():
    with pytest.raises(ValueError, match="The attribute 'key_columns' must not contain duplicate column names."):
        ImportConfig("config1", "file1.xlsx", "sheet1", "schema1", "table1", ImportMode.UPSERT, ("ID", "ID"))


@pytest.mark.parametrize(
    "mode, key_columns",
    [
        (ImportMode.UPSERT, ("ID",)), 
        (ImportMode.UPSERT, ("ReportDate", "Department")),
        (ImportMode.REPLACE, ()),
        (ImportMode.APPEND, ())
    ]
)
def test_import_config_accept_valid_key_columns(mode: ImportMode, key_columns: tuple[str, ...]):
    ImportConfig("config1", "file1.xlsx", "sheet1", "schema1", "table1", mode, key_columns)