from pathlib import Path
import sys

from src.import_excel import (
    configure_logging,
    create_run_id,
    get_config_path,
    parse_args,
    run,
)


def get_app_dir() -> Path:
    return Path(sys.argv[0]).resolve().parent


def main() -> int:
    args = parse_args()
    app_dir = get_app_dir()
    config_path = get_config_path(args.config, app_dir, Path.cwd())
    run_id = create_run_id()
    configure_logging(args.scheduled, config_path.parent, run_id)
    return int(run(app_dir, config_path, args.scheduled, run_id))


if __name__ == "__main__":
    sys.exit(main())