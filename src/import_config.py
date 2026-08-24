from dataclasses import dataclass
from enum import Enum


class ImportMode(Enum):
    REPLACE = "replace"
    APPEND = "append"


@dataclass(frozen=True)
class ImportConfig:
    name: str
    file: str
    sheet: str
    schema: str
    table: str
    mode: ImportMode = ImportMode.REPLACE

    def __post_init__(self) -> None:
        self._validate_attribute(self.name, 'name')
        self._validate_attribute(self.file, 'file')
        self._validate_attribute(self.sheet, 'sheet')
        self._validate_attribute(self.schema, 'schema')
        self._validate_attribute(self.table, 'table')

        if not isinstance(self.mode, ImportMode):
            raise TypeError(f"The attribute 'mode' must have a type 'ImportMode'")
        

    def _validate_attribute(self, value: str, attribute_name: str) -> None:
        if not isinstance(value, str):
            raise TypeError(f"The attribute '{attribute_name}' must have a type 'str'.")
        if not value.strip():
            raise ValueError(f"The attribute '{attribute_name}' should not be empty.")