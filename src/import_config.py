from dataclasses import dataclass


@dataclass(frozen=True)
class ImportConfig:
    name: str
    file: str
    sheet: str
    schema: str
    table: str

