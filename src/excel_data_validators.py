from pathlib import Path

import pandas as pd

from src.sql_meta_column import SqlMetaColumn
from src.import_config import ImportConfig
from src.value_validators import VALIDATOR_BY_SQL_TYPE


def validate_target_columns(root: Path, sql_meta_columns: list[SqlMetaColumn], import_config: ImportConfig) -> None:
    source_file = root / import_config.file
    df = pd.read_excel(
        source_file, 
        sheet_name=import_config.sheet,
        nrows=0,
        engine="openpyxl"
    )
    excel_columns = set(df.columns.to_list())
    sql_columns = set(column.name for column in sql_meta_columns)
    missing_columns = sql_columns - excel_columns
    extra_columns = excel_columns - sql_columns
    errors = []
    if missing_columns:
        errors.append(
            f"Excel source is missing columns required by "
            f"'{import_config.schema}.{import_config.table}': "
            f"{', '.join(sorted(missing_columns))}."
        )
    if extra_columns:
        errors.append(
            f"Excel source contains columns not present in "
            f"'{import_config.schema}.{import_config.table}': "
            f"{', '.join(sorted(extra_columns))}."
        )
    if errors:
        raise ValueError(f"Import '{import_config.name}':\n" + "\n".join(errors))


def validate_excel_data(root: Path, sql_meta_columns: list[SqlMetaColumn], import_config: ImportConfig) -> None:
    source_file = root / import_config.file
    df = pd.read_excel(source_file, sheet_name=import_config.sheet, engine="openpyxl")

    for column in sql_meta_columns:
        series = df[column.name]
        if not column.is_nullable and (count_na := series.isna().sum()) > 0:
            raise ValueError(
                f"Import '{import_config.name}':\n"
                f"Column '{column.name}' does not allow NULL values, but Excel contains {count_na} empty values."
            )

        validator = VALIDATOR_BY_SQL_TYPE.get(column.type_name)
        if validator is None:
            raise ValueError(
                f"Import '{import_config.name}':\n"
                f"SQL type '{column.type_name}' of column '{column.name}' is not supported."
            )
        validator(column, series.dropna())