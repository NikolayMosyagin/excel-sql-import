import argparse
from datetime import datetime
from dotenv import load_dotenv
import logging
import os
from pathlib import Path
import sys

from mssql_python import connect, Connection

from src.import_config import ImportConfig, ImportMode
from src.import_result import ImportResult
from src.import_task import ImportTask
from src.sql_meta_column import SqlMetaColumn
from src.config_loader import read_imports
from src.import_source_validators import validate_excel_sources, validate_import_sources
from src.excel_data_validators import validate_excel_data, validate_target_columns
from src.sql_metadata import get_sql_meta_columns, validate_target_tables
from src.sql_data_import import write_dataframe, upsert_dataframe, replace_by_columns_dataframe
from src.import_task_builder import build_manual_import_tasks, build_scheduled_import_tasks
from src.import_file_manager import (
    get_processing_run_dir,
    get_processed_run_dir,
    create_processing_run_dir,
    move_source_files,
    archive_processing_run
)
from src.excel_utils import prepare_excel_dataframe
from src.path_utils import resolve_path


logger = logging.getLogger(__name__)


def create_run_id() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def configure_logging(
    scheduled: bool, 
    config_dir: Path,
    run_id: str,
) -> None:

    handlers = [logging.StreamHandler()]

    if scheduled:
        logs_dir = config_dir / "logs"
        logs_dir.mkdir(exist_ok=True)

        log_path = logs_dir / f"import_{run_id}.log"

        handlers.append(
            logging.FileHandler(log_path, encoding="utf-8")
        )

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=handlers,
        force=True
    )


def get_root_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent

    return Path(__file__).resolve().parents[1]


def get_config_path(
    config: str | None,
    app_dir: Path,
    current_dir: Path
) -> Path:
    return (
        resolve_path(config, current_dir) 
        if config is not None 
        else app_dir / "config" / "imports.toml"
    )
        

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import Excel data into SQL Server using a TOML configuration file."
    )
    parser.add_argument(
        "-c", 
        "--config",
        type=str,
        default=None,
        metavar="PATH",
        help=(
            "Path to the TOML configuration file. "
            "Relative paths are resolved from the current working directory. "
            "If omitted, 'config/imports.toml' in the application directory is used."
        )
    )
    parser.add_argument(
        "--scheduled",
        action="store_true",
        help="Enable scheduled execution mode."
    )
    return parser.parse_args(argv)

    
def import_excel_data(
    working_file: Path, 
    conn: Connection, 
    sql_meta_columns: list[SqlMetaColumn], 
    import_config: ImportConfig
) -> ImportResult:
    
    df = prepare_excel_dataframe(
        working_file,
        import_config.sheet,
        import_config.column_mapping,
        import_config.date_formats
    )

    column_names = [column.name for column in sql_meta_columns]

    match import_config.mode:
        case ImportMode.UPSERT:
            return upsert_dataframe(conn, df, column_names, import_config)

        case ImportMode.REPLACE_BY_COLUMNS:
            return replace_by_columns_dataframe(conn, df, column_names, import_config)

        case ImportMode.REPLACE | ImportMode.APPEND:
            return write_dataframe(conn, df, column_names, import_config)


def import_all_data(
    conn: Connection, 
    import_tasks: list[ImportTask],
    sql_meta_columns: list[list[SqlMetaColumn]]
) -> None:
    results = []
    try:
        for import_task, meta_columns in zip(import_tasks, sql_meta_columns, strict=True):
            import_config = import_task.config

            logger.info(
                "Importing '%s': %s -> %s.%s (mode: %s)",
                import_config.name,
                import_task.working_file,
                import_config.schema,
                import_config.table,
                import_config.mode.value
            )

            result = import_excel_data(import_task.working_file, conn, meta_columns, import_config)
            results.append(result)
        conn.commit()
    except Exception:
        conn.rollback()
        logger.warning("Transaction rolled back.")
        raise

    logger.info("Transaction committed.")
    for import_task, import_result in zip(import_tasks, results, strict=True):
        log_import_result(import_task.config, import_result)


def log_import_result(
    import_config: ImportConfig,
    import_result: ImportResult
)-> None:
    match import_config.mode:
        case ImportMode.REPLACE:
            logger.info(
                "Import '%s' completed: %d row(s) deleted, %d row(s) inserted.",
                import_config.name,
                import_result.deleted,
                import_result.inserted
            )
        case ImportMode.APPEND:
            logger.info(
                "Import '%s' completed: %d row(s) inserted.",
                import_config.name,
                import_result.inserted
            )
        case ImportMode.UPSERT:
            logger.info(
                "Import '%s' completed: %d row(s) updated, %d row(s) inserted.",
                import_config.name,
                import_result.updated,
                import_result.inserted
            )
        case ImportMode.REPLACE_BY_COLUMNS:
            logger.info(
                "Import '%s' completed: %d row(s) deleted, %d row(s) inserted.",
                import_config.name,
                import_result.deleted,
                import_result.inserted
            )


def main(
    app_dir: Path,
    config_path: Path,
    scheduled: bool,
    run_id: str
) -> None:
    load_dotenv(app_dir / ".env")
    logger.info("Using config: %s", config_path)

    import_configs = read_imports(config_path)
    logger.info("Loaded %d import configuration(s).", len(import_configs))

    logger.info("Validating source files.")
    config_dir = config_path.parent

    if scheduled:
        processing_run_dir = get_processing_run_dir(config_dir, run_id)
        import_tasks = build_scheduled_import_tasks(config_dir, import_configs, processing_run_dir)
    else:
        import_tasks = build_manual_import_tasks(config_dir, import_configs)

    validate_import_sources(import_tasks)

    if scheduled:
        create_processing_run_dir(processing_run_dir)
        move_source_files(import_tasks)

    logger.info("Validating Excel sources.")
    validate_excel_sources(import_tasks)
    sql_connection_string = os.getenv("SQL_CONNECTION_STRING")
    if sql_connection_string is None or sql_connection_string.strip() == "":
        raise ValueError("Required environment variable 'SQL_CONNECTION_STRING' is not set or is empty.")
    
    with connect(sql_connection_string) as conn:
        logger.info("Validating target tables and import data.")
        validate_target_tables(conn, import_configs)
        sql_columns = get_sql_meta_columns(conn, import_configs)
        for import_task, sql_column in zip(import_tasks, sql_columns, strict=True):
            validate_target_columns(sql_column, import_task)
            validate_excel_data(sql_column, import_task)
        logger.info("Validation completed successfully.")
        import_all_data(conn, import_tasks, sql_columns)

    if scheduled:
        processed_run_dir = get_processed_run_dir(config_dir, run_id)
        archive_processing_run(processing_run_dir, processed_run_dir)


def run(
    app_dir: Path,
    config_path: Path,
    scheduled: bool,
    run_id: str
) -> int:
    try:
        logger.info("Import started.")
        main(app_dir, config_path, scheduled, run_id)
        logger.info("Import completed successfully.")
        return 0
    except Exception:
        logger.exception("Import failed.")
        return 1


if __name__ == '__main__':
    args = parse_args()
    app_dir = get_root_path()
    config_path = get_config_path(args.config, app_dir, Path.cwd())
    config_dir = config_path.parent
    run_id = create_run_id()
    configure_logging(args.scheduled, config_dir, run_id)
    sys.exit(run(app_dir, config_path, args.scheduled, run_id))