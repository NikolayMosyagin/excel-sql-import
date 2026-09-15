from pathlib import Path

from src.import_task import ImportTask
from src.import_config import ImportConfig
from src.path_utils import resolve_path


def get_unique_source_files(
    base_dir: Path,
    import_configs: list[ImportConfig]
) -> list[Path]:

    unique_files = []
    for import_config in import_configs:
        source_file = resolve_path(import_config.file, base_dir)
        if source_file not in unique_files:
            unique_files.append(source_file)

    return unique_files


def build_manual_import_tasks(
    base_dir: Path,
    import_configs: list[ImportConfig]
) -> list[ImportTask]:

    import_tasks = []
    for config in import_configs:
        source_file = resolve_path(config.file, base_dir)
        import_tasks.append(
            ImportTask(
                config,
                source_file,
                source_file
            ))
    return import_tasks


def build_scheduled_import_tasks(
    base_dir: Path,
    import_configs: list[ImportConfig],
    processing_run_dir: Path
) -> list[ImportTask]:

    import_tasks = []
    unique_files = get_unique_source_files(base_dir, import_configs)

    working_files_by_source = {
        file: processing_run_dir / f"{(num + 1):03}_{file.name}"
        for num, file in enumerate(unique_files)
    }

    for import_config in import_configs:
        source_file = resolve_path(import_config.file, base_dir)
        import_tasks.append(
            ImportTask(
                import_config,
                source_file,
                working_files_by_source[source_file]
            )
        )
    return import_tasks