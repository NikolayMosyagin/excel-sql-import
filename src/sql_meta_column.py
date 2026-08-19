from dataclasses import dataclass


@dataclass(frozen=True)
class SqlMetaColumn:
    name: str
    type_name: str
    max_length: int
    precision: int
    scale: int
    is_nullable: bool