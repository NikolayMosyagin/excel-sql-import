from dataclasses import dataclass


@dataclass(frozen=True)
class ImportConfig:
    name: str
    file: str
    sheet: str
    schema: str
    table: str

    def __post_init__(self) -> None:
        self._validate_attribute(self.name, 'name')
        self._validate_attribute(self.file, 'file')
        self._validate_attribute(self.sheet, 'sheet')
        self._validate_attribute(self.schema, 'schema')
        self._validate_attribute(self.table, 'table')

    def _validate_attribute(self, value: str, attribute_name: str) -> None:
        if not isinstance(value, str):
            raise TypeError(f"The attribute '{attribute_name}' must have a type 'str'.")
        if not value.strip():
            raise ValueError(f"The attribute '{attribute_name}' should not be empty.")




