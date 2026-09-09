import argparse
from datetime import datetime
from dotenv import load_dotenv
import logging
import os
from pathlib import Path
import sys

from mssql_python import connect, Connection

from src.import_config import ImportConfig, ImportMode
from src.sql_meta_column import SqlMetaColumn
from src.config_loader import read_imports
from src.import_source_validators import validate_excel_sources, validate_import_sources
from src.excel_data_validators import validate_excel_data, validate_target_columns
from src.sql_metadata import get_sql_meta_columns, validate_target_tables
from src.sql_data_import import write_dataframe, upsert_dataframe
from src.excel_utils import prepare_excel_dataframe
from src.path_utils import resolve_path


logger = logging.getLogger(__name__)


def configure_logging(scheduled: bool, config_dir: Path) -> None:

    handlers = [logging.StreamHandler()]

    if scheduled:
        logs_dir = config_dir / "logs"
        logs_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        log_path = logs_dir / f"import_{timestamp}.log"

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
    source_file: Path, 
    conn: Connection, 
    sql_meta_columns: list[SqlMetaColumn], 
    import_config: ImportConfig
) -> None:
    
    df = prepare_excel_dataframe(
        source_file,
        import_config.sheet,
        import_config.column_mapping,
        import_config.date_formats
    )

    column_names = [column.name for column in sql_meta_columns]

    if import_config.mode == ImportMode.UPSERT:
        upsert_dataframe(conn, df, column_names, import_config)
    else:
        write_dataframe(conn, df, column_names, import_config)


def import_all_data(
    base_dir: Path,
    conn: Connection, 
    import_configs: list[ImportConfig],
    sql_columns: list[list[SqlMetaColumn]]
) -> None:
    try:
        for import_config, sql_column in zip(import_configs, sql_columns, strict=True):
            source_file = resolve_path(import_config.file, base_dir)

            logger.info(
                "Importing '%s': %s -> %s.%s (mode: %s)",
                import_config.name,
                source_file,
                import_config.schema,
                import_config.table,
                import_config.mode.value
            )

            import_excel_data(source_file, conn, sql_column, import_config)

            logger.info(
                "Import '%s' completed.",
                import_config.name
            )
        conn.commit()
        logger.info("Transaction committed.")
    except Exception:
        conn.rollback()
        logger.warning("Transaction rolled back.")
        raise


def main(app_dir: Path, config_path: Path) -> None:
    load_dotenv(app_dir / ".env")
    logger.info("Using config: %s", config_path)

    import_configs = read_imports(config_path)
    logger.info("Loaded %d import configuration(s).", len(import_configs))

    logger.info("Validating import sources and target tables.")
    config_dir = config_path.parent
    validate_import_sources(config_dir, import_configs)
    validate_excel_sources(config_dir, import_configs)
    sql_connection_string = os.getenv("SQL_CONNECTION_STRING")
    if sql_connection_string is None or sql_connection_string.strip() == "":
        raise ValueError("Required environment variable 'SQL_CONNECTION_STRING' is not set or is empty.")
    
    with connect(sql_connection_string) as conn:
        validate_target_tables(conn, import_configs)
        sql_columns = get_sql_meta_columns(conn, import_configs)
        for import_config, sql_column in zip(import_configs, sql_columns, strict=True):
            source_file = resolve_path(import_config.file, config_dir)
            validate_target_columns(source_file, sql_column, import_config)
            validate_excel_data(source_file, sql_column, import_config)
        logger.info("Validation completed successfully.")
        import_all_data(config_dir, conn, import_configs, sql_columns)


def run(app_dir: Path, config_path: Path) -> int:
    try:
        logger.info("Import started.")
        main(app_dir, config_path)
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
    configure_logging(args.scheduled, config_dir)
    sys.exit(run(app_dir, config_path))