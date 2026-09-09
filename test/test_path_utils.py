from pathlib import Path

from src.path_utils import resolve_path


def test_resolve_path_relative_str(tmp_path: Path):
    relative_path = "data/test.xlsx"
    assert resolve_path(relative_path, tmp_path) == tmp_path / relative_path


def test_resolve_path_relative_path(tmp_path: Path):
    file_path = Path("data/test.xlsx")
    assert resolve_path(file_path, tmp_path) == tmp_path / file_path


def test_resolve_path_absolute_path(tmp_path: Path):
    base_dir = tmp_path / "other"
    file_path = tmp_path / "data" / "test.xlsx"
    assert resolve_path(file_path, base_dir) == file_path


def test_resolve_path_absolute_str(tmp_path: Path):
    file_path = tmp_path / "data" / "test.xlsx"
    assert resolve_path(str(file_path), tmp_path / "other") == file_path
    

def test_resolve_path_normalize(tmp_path: Path):
    file_path = tmp_path / "data" / "test" / ".." / "test.xlsx"
    assert resolve_path(file_path, tmp_path) == tmp_path / "data" / "test.xlsx"