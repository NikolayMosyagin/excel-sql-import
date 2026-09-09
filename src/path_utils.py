from pathlib import Path


def resolve_path(path: str | Path, base_dir: Path) -> Path:
    if isinstance(path, str):
        path = Path(path)
    
    return (path if path.is_absolute() else base_dir / path).resolve()