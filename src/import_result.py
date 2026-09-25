from dataclasses import dataclass


@dataclass(frozen=True)
class ImportResult:
    inserted: int = 0
    updated: int = 0
    deleted: int = 0