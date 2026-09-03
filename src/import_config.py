from dataclasses import dataclass, field
from types import MappingProxyType
from collections.abc import Mapping
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
    column_mapping: Mapping[str, str] = field(default_factory=dict)

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

        if not isinstance(self.column_mapping, Mapping):
            raise TypeError("The attribute 'column_mapping' must be of type 'Mapping'.")

        if any(not isinstance(value, str) for value in self.column_mapping):
            raise TypeError("All keys of 'column_mapping' must be strings.")
        if any(not isinstance(value, str) for value in self.column_mapping.values()):
            raise TypeError("All values of 'column_mapping' must be strings.")
        if any(key.strip() == "" or value.strip() == "" for key, value in self.column_mapping.items()):
            raise ValueError("The attribute 'column_mapping' must contain only non-empty column names.")
        if len(set(self.column_mapping.values())) != len(self.column_mapping):
            raise ValueError(
                "The attribute 'column_mapping' must not map multiple Excel columns "
                "to the same SQL column."
            )
        object.__setattr__(self, "column_mapping", MappingProxyType(dict(self.column_mapping)))                
            
    def _validate_attribute(self, value: str, attribute_name: str) -> None:
        if not isinstance(value, str):
            raise TypeError(f"The attribute '{attribute_name}' must be of type 'str'.")
        if not value.strip():
            raise ValueError(f"The attribute '{attribute_name}' must not be empty.")