from pathlib import Path

import pandas as pd
import pytest

from src.import_file_manager import (
    get_processing_run_dir,
    get_processed_run_dir,
    archive_processing_run,
    create_processing_run_dir,
    move_source_files
)
from src.import_task import ImportTask
from src.import_config import ImportConfig


def test_get_processing_run_dir(tmp_path: Path):
    run_id = "12"
    result = get_processing_run_dir(tmp_path, run_id)
    assert result == tmp_path / "processing" / run_id


def test_get_processed_run_dir(tmp_path: Path):
    run_id = "123"
    result = get_processed_run_dir(tmp_path, run_id)

    assert result == tmp_path / "processed" / run_id


def test_archive_processing_run_moves_run_to_processed(tmp_path: Path):
    run_id = "123"
    processing_run_dir = tmp_path / "processing" / run_id
    processing_run_dir.mkdir(parents=True)
    data_file = processing_run_dir / "data.txt"
    data_file.write_text("Test", encoding="utf-8")
    processed_run_dir = tmp_path / "processed" / run_id
    archive_processing_run(processing_run_dir, processed_run_dir)

    assert not processing_run_dir.exists()
    assert processed_run_dir.exists()
    data_file_new = processed_run_dir / "data.txt"
    assert data_file_new.exists()
    assert data_file_new.read_text() == "Test"


def test_archive_processing_run_rejects_existing_processed_run(tmp_path: Path):
    run_id = "123"
    processing_run_dir = tmp_path / "processing" / run_id
    processing_run_dir.mkdir(parents=True)
    data_file = processing_run_dir / "data.txt"
    data_file.write_text("Test", encoding="utf-8")
    processed_run_dir = tmp_path / "processed" / run_id
    processed_run_dir.mkdir(parents=True)
    with pytest.raises(FileExistsError):
        archive_processing_run(processing_run_dir, processed_run_dir)


def test_create_processing_run_dir_accepts(tmp_path: Path):
    run_id = "2000-05-31_22-30-31"
    processing_run_dir = tmp_path / "processing" / run_id
    create_processing_run_dir(processing_run_dir)
    assert processing_run_dir.exists()
    assert processing_run_dir.is_dir()


def test_create_processing_run_dir_rejects_run_id_dir_exist(tmp_path: Path):
    run_id = "2000-05-31_22-30-31"
    processing_run_dir = tmp_path / "processing" / run_id
    processing_run_dir.mkdir(parents=True)
    with pytest.raises(FileExistsError):
        create_processing_run_dir(processing_run_dir)


def test_move_source_files_one_source_file(tmp_path: Path):
    source_file = tmp_path / "test.xlsx"
    source_df = pd.DataFrame({
        "Column1": [1, 2],
        "Column2": [1, 2]
    })
    source_df.to_excel(source_file, sheet_name="sheet1", index=False)
    processing_dir = tmp_path / "processing"
    processing_dir.mkdir()
    working_file = processing_dir / "001_test.xlsx"
    import_tasks = [
        ImportTask(
            ImportConfig("name1", "test.xlsx", "sheet1", "schema1", "table1"),
            source_file,
            working_file
        ),
        ImportTask(
            ImportConfig("name2", "data/test.xlsx", "sheet2", "schema1", "table2"),
            source_file,
            working_file
        )
    ]

    move_source_files(import_tasks)

    assert working_file.exists()
    assert not source_file.exists()
    df = pd.read_excel(working_file, sheet_name="sheet1", engine="openpyxl")
    assert df.equals(source_df)


def test_move_source_files_two_different_source_file(tmp_path: Path):
    processing_dir = tmp_path / "processing"
    processing_dir.mkdir()
    source_df = pd.DataFrame({
        "Column1": [1, 2],
        "Column2": [12, 24]
    })
    import_tasks = [
        ImportTask(
            ImportConfig("name1", "test1.xlsx", "sheet1", "schema1", "table1"),
            tmp_path / "test1.xlsx",
            processing_dir / "001_test1.xlsx"
        ),
        ImportTask(
            ImportConfig("name2", "test2.xlsx", "sheet1", "schema1", "table2"),
            tmp_path / "test2.xlsx",
            processing_dir / "002_test2.xlsx"
        )
    ]
    for import_task in import_tasks:
        source_df.to_excel(import_task.source_file, sheet_name="sheet1", index=False)

    move_source_files(import_tasks)
    assert all(import_task.working_file.exists() for import_task in import_tasks)
    assert all(not import_task.source_file.exists() for import_task in import_tasks)
    assert all(
        pd.read_excel(import_task.working_file, sheet_name="sheet1", engine="openpyxl").equals(source_df)
        for import_task in import_tasks
    )