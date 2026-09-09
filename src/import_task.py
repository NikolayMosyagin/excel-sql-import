from dataclasses import dataclass
from pathlib import Path

from src.import_config import ImportConfig

@dataclass(frozen=True)
class ImportTask:
    config: ImportConfig
    source_file: Path
    working_file: Path
