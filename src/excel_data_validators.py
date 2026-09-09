from pathlib import Path
from collections.abc import Mapping

import pandas as pd

from src.sql_meta_column import SqlMetaColumn
from src.import_config import ImportConfig, ImportMode
from src.excel_utils import read_excel_dataframe, prepare_excel_dataframe
from src.value_validators import VALIDATOR_BY_SQL_TYPE


DATE_SQL_TYPES = {
        "date",
        "smalldatetime",
        "datetime",
        "datetime2",
}

def validate_excel_columns(
    df: pd.DataFrame,
    sql_columns: set[str],
    table_name: str
) -> list[str]:
    errors = []

    duplicated_columns = sorted(
        set(df.columns[df.columns.duplicated()].tolist())
    )
    if duplicated_columns:
        errors.append(
            f"Excel source contains duplicate column names after applying column mapping: "
            f"{", ".join(duplicated_columns)}"
        )

    excel_columns = set(df.columns.to_list())
    missing_columns = sql_columns - excel_columns
    extra_columns = excel_columns - sql_columns

    if missing_columns:
        errors.append(
            f"Excel source is missing columns required by "
            f"'{table_name}': "
            f"{', '.join(sorted(missing_columns))}."
        )
    if extra_columns:
        errors.append(
            f"Excel source contains columns not present in "
            f"'{table_name}': "
            f"{', '.join(sorted(extra_columns))}."
        )
    return errors


def validate_date_format_columns(
    excel_columns: set[str],
    sql_meta_columns: list[SqlMetaColumn],
    date_formats: Mapping[str, str]
) -> list[str]:

    errors = []
    missing_date_format_columns = sorted(
        column_name 
        for column_name in date_formats
        if column_name not in excel_columns
    )
    if missing_date_format_columns:
        errors.append(
            f"Columns from 'date_formats' are not present in Excel "
            f"after applying column mapping: "
            f"{', '.join(missing_date_format_columns)}."
        )

    invalid_date_format_columns = []
    for column_name in date_formats:
        sql_column = next((value for value in sql_meta_columns if value.name == column_name), None)
        if sql_column is None or sql_column.type_name in DATE_SQL_TYPES:
            continue

        invalid_date_format_columns.append(
            f"{sql_column.name} ({sql_column.type_name})"
        )

    if invalid_date_format_columns:
        errors.append(
            f"'date_formats' can only be used for SQL date/time columns, but got: "
            f"{", ".join(invalid_date_format_columns)}."
        )
    return errors


def validate_upsert_key_columns(
    import_config: ImportConfig,
    sql_columns: set[str]
) -> list[str]:
    
    errors = []
    if import_config.mode != ImportMode.UPSERT:
        return errors

    key_columns_set = set(import_config.key_columns)
    missing_key_columns = key_columns_set - sql_columns
    if missing_key_columns:
        errors.append(
            f"Key columns are not present in target table "
            f"'{import_config.schema}.{import_config.table}': "
            f"{', '.join(sorted(missing_key_columns))}."
        )

    return errors


def validate_target_columns(
    source_file: Path, 
    sql_meta_columns: list[SqlMetaColumn], 
    import_config: ImportConfig
) -> None:

    df = read_excel_dataframe(
        source_file, 
        import_config.sheet, 
        import_config.column_mapping,
        nrows=0
    )

    errors = []

    sql_columns = set(column.name for column in sql_meta_columns)

    errors.extend(
        validate_excel_columns(
            df,
            sql_columns,
            f"{import_config.schema}.{import_config.table}"
        )
    )

    errors.extend(
        validate_date_format_columns(
            set(df.columns),
            sql_meta_columns,
            import_config.date_formats
        )
    )

    errors.extend(
        validate_upsert_key_columns(
            import_config,
            sql_columns,
        )
    )

    if errors:
        raise ValueError(f"Import '{import_config.name}':\n" + "\n".join(errors))
    

def validate_excel_data(
    source_file: Path,
    sql_meta_columns: list[SqlMetaColumn],
    import_config: ImportConfig
) -> None:

    df = prepare_excel_dataframe(
        source_file, 
        import_config.sheet,
        import_config.column_mapping,
        import_config.date_formats
    )

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