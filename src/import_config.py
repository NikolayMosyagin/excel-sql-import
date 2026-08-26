from dataclasses import dataclass
from enum import Enum


class ImportMode(Enum):
    REPLACE = "replace"
    APPEND = "append"
    UPSERT = "upsert"


@dataclass(frozen=True)
class ImportConfig:
    name: str
    file: str
    sheet: str
    schema: str
    table: str
    mode: ImportMode = ImportMode.REPLACE
    key_columns: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        self._validate_attribute(self.name, 'name')
        self._validate_attribute(self.file, 'file')
        self._validate_attribute(self.sheet, 'sheet')
        self._validate_attribute(self.schema, 'schema')
        self._validate_attribute(self.table, 'table')

        if not isinstance(self.mode, ImportMode):
            raise TypeError(f"The attribute 'mode' must be of type 'ImportMode'.")

        if not isinstance(self.key_columns, tuple):
            raise TypeError(f"The attribute 'key_columns' must be of type 'tuple'.")

        match self.mode:
            case ImportMode.REPLACE | ImportMode.APPEND:
                if self.key_columns:
                    raise ValueError(f"The attribute 'key_columns' must be empty for mode '{self.mode.value}'.")
            case ImportMode.UPSERT:
                if not self.key_columns:
                    raise ValueError(f"The attribute 'key_columns' must not be empty for mode '{self.mode.value}'.")
                if any(not isinstance(value, str) for value in self.key_columns):
                    raise TypeError(f"All elements of 'key_columns' must be strings.")
                if any(value.strip() == "" for value in self.key_columns):
                    raise ValueError(f"The attribute 'key_columns' must contain only non-empty strings.")
                if len(set(self.key_columns)) != len(self.key_columns):
                    raise ValueError(f"The attribute 'key_columns' must not contain duplicate column names.")
            case _:
                raise ValueError(f"Validation rules are not defined for mode '{self.mode.value}'.")
                
            
    def _validate_attribute(self, value: str, attribute_name: str) -> None:
        if not isinstance(value, str):
            raise TypeError(f"The attribute '{attribute_name}' must have a type 'str'.")
        if not value.strip():
            raise ValueError(f"The attribute '{attribute_name}' should not be empty.")