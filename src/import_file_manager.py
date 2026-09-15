from pathlib import Path
import shutil

from src.import_task import ImportTask


def get_processing_run_dir(config_dir: Path, run_id: str) -> Path:
    return config_dir / "processing" / run_id


def get_processed_run_dir(config_dir: Path, run_id: str) -> Path:
    return config_dir / "processed" / run_id


def create_processing_run_dir(processing_run_dir: Path) -> None:
    processing_dir = processing_run_dir.parent
    processing_dir.mkdir(parents=True, exist_ok=True)
    processing_run_dir.mkdir()


def archive_processing_run(
    processing_run_dir: Path,
    processed_run_dir: Path
) -> None:

    processed_dir = processed_run_dir.parent
    processed_dir.mkdir(exist_ok=True)
    if processed_run_dir.exists():
        raise FileExistsError(
            f"Processed run directory already exists: '{processed_run_dir}'. "
            "Refusing to overwrite or merge archived files.")
    shutil.move(processing_run_dir, processed_run_dir)


def move_source_files(import_tasks: list[ImportTask]) -> None:
    moved_files = set()
    for import_task in import_tasks:
        if import_task.source_file in moved_files:
            continue
        shutil.move(import_task.source_file, import_task.working_file)
        moved_files.add(import_task.source_file)