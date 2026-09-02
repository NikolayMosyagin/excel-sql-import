from pathlib import Path

import pandas as pd

from src.sql_meta_column import SqlMetaColumn
from src.import_config import ImportConfig, ImportMode
from src.excel_utils import get_excel_engine
from src.value_validators import VALIDATOR_BY_SQL_TYPE


def validate_target_columns(root: Path, sql_meta_columns: list[SqlMetaColumn], import_config: ImportConfig) -> None:
    source_file = root / import_config.file
    df = pd.read_excel(
        source_file, 
        sheet_name=import_config.sheet,
        nrows=0,
        engine=get_excel_engine(source_file)
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

    if import_config.mode == ImportMode.UPSERT:
        key_columns_set = set(import_config.key_columns)
        missing_key_columns = key_columns_set - sql_columns
        if missing_key_columns:
            errors.append(
                f"Key columns are not present in target table "
                f"'{import_config.schema}.{import_config.table}': "
                f"{', '.join(sorted(missing_key_columns))}."
            )

    if errors:
        raise ValueError(f"Import '{import_config.name}':\n" + "\n".join(errors))


def validate_excel_data(root: Path, sql_meta_columns: list[SqlMetaColumn], import_config: ImportConfig) -> None:
    source_file = root / import_config.file
    df = pd.read_excel(
        source_file, 
        sheet_name=import_config.sheet, 
        engine=get_excel_engine(source_file))

    if import_config.mode == ImportMode.UPSERT:
        for column in import_config.key_columns:
            series = df[column]
            if (count_na := series.isna().sum()) > 0:
                raise ValueError(
                    f"Import '{import_config.name}':\n"
                    f"Key column '{column}' cannot contain NULL values for UPSERT, "
                    f"but Excel contains {count_na} empty values."
                )

        duplicated_mask = df.duplicated(subset=import_config.key_columns, keep=False)
        if duplicated_mask.any():
            duplicate_rows = (df.index[duplicated_mask] + 2).tolist()
            raise ValueError(
                f"Import '{import_config.name}':\n"
                f"Excel contains duplicate values for UPSERT key columns "
                f"'{', '.join(import_config.key_columns)}'. "
                f"Duplicate rows: {', '.join(str(row) for row in duplicate_rows)}."
            )

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