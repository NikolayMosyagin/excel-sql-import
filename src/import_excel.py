from pathlib import Path
from decimal import Decimal
import os
import tomllib
import pandas as pd
from dotenv import load_dotenv

from mssql_python import connect, Connection

from src.import_config import ImportConfig
from src.sql_meta_column import SqlMetaColumn


def validate_string_values(sql_column: SqlMetaColumn, series: pd.Series) -> None:
    unlimited_length = (
        sql_column.type_name in ('varchar', 'nvarchar') 
        and sql_column.max_length == -1
    )

    if not unlimited_length:
        max_length = (
            sql_column.max_length 
            if sql_column.type_name in ('varchar', 'char') else 
            (sql_column.max_length // 2)
        )

    for index, value in series.items():
        excel_row = index + 2

        if not isinstance(value, str):
            raise ValueError(
                f"Column '{sql_column.name}', row {excel_row}: "
                f"expected a string value, but got '{value}' "
                f"of type '{type(value).__name__}'."
            )

        if not unlimited_length and len(value) > max_length:
            raise ValueError(
                f"Column '{sql_column.name}', row {excel_row}: "
                f"value exceeds the maximum length of {max_length} characters "
                f"(got {len(value)})."
            )
        

def validate_integer_values(sql_column: SqlMetaColumn, series: pd.Series) -> None:
    for index, value in series.items():
        excel_row = index + 2
        type_value = type(value)
        if type_value is not int and (type_value is not float or not value.is_integer()):
            raise ValueError(
                f"Column '{sql_column.name}', row {excel_row}: "
                f"expected an integer value, but got '{value}' "
                f"of type '{type(value).__name__}'."
            )
        min_value, max_value = MINMAX_VALUE_BY_SQL_TYPE[sql_column.type_name]
        int_value = int(value)
        if int_value < min_value or int_value > max_value:
            raise ValueError(
                f"Column '{sql_column.name}', row {excel_row}: "
                f"value must be between {min_value} and {max_value}, but got {int_value}."
            )

        
def validate_decimal_values(sql_column: SqlMetaColumn, series: pd.Series) -> None:
    for index, value in series.items():
        excel_row = index + 2
        if type(value) not in (int, float):
            raise ValueError(
                f"Column '{sql_column.name}', row {excel_row}: "
                f"expected a numeric value, but got '{value}' "
                f"of type '{type(value).__name__}'."
            )

        normalized_value = Decimal(str(value)).normalize()
        decimal_tuple = normalized_value.as_tuple()
        fraction_digits = max(-decimal_tuple.exponent, 0)
        integer_digits = max(len(decimal_tuple.digits) + decimal_tuple.exponent, 0)
        if integer_digits == 1 and decimal_tuple.digits[0] == 0:
            integer_digits = 0
        if fraction_digits > sql_column.scale or integer_digits > sql_column.precision - sql_column.scale:
            raise ValueError(
                f"Column '{sql_column.name}', row {excel_row}: "
                f"value '{value}' does not fit decimal({sql_column.precision}, {sql_column.scale}): "
                f"allowed up to {sql_column.precision - sql_column.scale} integer digits "
                f"and {sql_column.scale} fractional digits, but got {integer_digits} and {fraction_digits}."
            )


def validate_float_values(sql_column: SqlMetaColumn, series: pd.Series) -> None:
    pass


def validate_datetime_values(sql_column: SqlMetaColumn, series: pd.Series) -> None:
    pass


VALIDATOR_BY_SQL_TYPE = {
    "varchar": validate_string_values,
    "nvarchar": validate_string_values,
    "char": validate_string_values,
    "nchar": validate_string_values,

    "tinyint": validate_integer_values,
    "smallint": validate_integer_values,
    "int": validate_integer_values,
    "bigint": validate_integer_values,

    "decimal": validate_decimal_values,
    "numeric": validate_decimal_values,

    "float": validate_float_values,
    "real": validate_float_values,

    "date": validate_datetime_values,
    "datetime": validate_datetime_values,
    "datetime2": validate_datetime_values,
    "smalldatetime": validate_datetime_values
}

MINMAX_VALUE_BY_SQL_TYPE = {
    "tinyint": (0, 2**8 - 1),
    "smallint": (-2**15, 2**15 - 1),
    "int": (-2**31, 2**31 - 1),
    "bigint": (-2**63, 2**63 - 1)
}


def read_imports(root: Path) -> list[ImportConfig]:
    imports_path = root / 'config' / 'imports.toml'
    IMPORTS_KEY = 'imports'
    if not imports_path.exists():
        raise FileNotFoundError(f"Configuration file not found: '{imports_path}'.")
    
    with open(imports_path, "rb") as imports_file:
        data = tomllib.load(imports_file)

    if IMPORTS_KEY not in data:
        raise ValueError(f"Required configuration key '{IMPORTS_KEY}' is missing.")

    imports = data[IMPORTS_KEY]
    if not isinstance(imports, list):
        raise TypeError(f"Configuration key '{IMPORTS_KEY}' must be a list.")
    if not imports:
        raise ValueError(f"Configuration key '{IMPORTS_KEY}' cannot be empty.")
    
    import_configs: list[ImportConfig] = []
    for import_data in imports:
        if not isinstance(import_data, dict):
            raise TypeError(f"Import configuration must be a dictionary.")
        try:
            import_configs.append(ImportConfig(**import_data))
        except (TypeError, ValueError) as original_error:
            raise ValueError(
                f"Invalid import configuration '{import_data.get('name', 'unknown')}':\n"
                f"{original_error}"
            ) from original_error
    return import_configs


def validate_import_sources(root: Path, import_configs: list[ImportConfig]) -> None:
    for import_config in import_configs:
        source_file = root / import_config.file
        if not source_file.exists():
            raise FileNotFoundError(f"Source file not found: '{source_file}'.")
    
        if source_file.is_dir():
            raise IsADirectoryError(f"Expected a file, but found a directory: '{source_file}'.")


def validate_excel_sources(root: Path, import_configs: list[ImportConfig]) -> None:
    for import_config in import_configs:
        source_file = root / import_config.file
        with pd.ExcelFile(source_file, engine='openpyxl') as excel_file:
            if import_config.sheet not in excel_file.sheet_names:
                raise ValueError(f"Source file '{source_file}' doesn't contain sheet '{import_config.sheet}'.")
            df = excel_file.parse(sheet_name=import_config.sheet, nrows=1)
        
        if df.empty:
            raise ValueError(f"Sheet '{import_config.sheet}' in source file '{source_file}' is empty.")


def validate_target_tables(conn: Connection, import_configs: list[ImportConfig]) -> None:
    check_query = """
SELECT 1
FROM sys.tables AS t
JOIN sys.schemas as s
	ON s.schema_id = t.schema_id
WHERE s.name = %(schema)s
	AND t.name = %(table)s"""
    for import_config in import_configs:
        with conn.cursor() as cursor:
            cursor.execute(check_query, {'schema': import_config.schema, 'table': import_config.table})
            row_data = cursor.fetchone()
            if row_data is None:
                raise ValueError(f"Target table '{import_config.schema}.{import_config.table}' does not exist.")


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

        

def import_excel_data(
        root: Path, 
        conn: Connection, 
        sql_meta_columns: list[SqlMetaColumn], 
        import_config: ImportConfig
) -> None:
    source_file = root / import_config.file
    df = pd.read_excel(source_file, sheet_name=import_config.sheet, engine="openpyxl")
    column_names = [column.name for column in sql_meta_columns]
    df = df[column_names]

    rows = df.shape[0]
    target_table = (
        f"{quote_identifier(import_config.schema)}."
        f"{quote_identifier(import_config.table)}"
    )

    batch_size = 1000
    delete_query = f"DELETE FROM {target_table}"
    insert_query = f"""
INSERT INTO {target_table}
({', '.join(quote_identifier(name) for name in column_names)})
VALUES({', '.join('?' for _ in range(len(column_names)))})"""
    try:
        with conn.cursor() as cursor:
            cursor.execute(delete_query)
            index = 0
            while index < rows:
                values = [
                    normalize_row(row) 
                    for row in df.iloc[index:index+batch_size].itertuples(index=False, name=None)
                ]
                cursor.executemany(insert_query, values)
                index += batch_size
            conn.commit()
    except Exception:
        conn.rollback()
        raise


def get_sql_meta_columns(conn: Connection, import_configs: list[ImportConfig]) -> list[list[SqlMetaColumn]]:
    get_columns_query = """
SELECT 
    c.name,
	types.name as type_name,
	c.max_length,
	c.precision,
	c.scale,
	c.is_nullable
FROM sys.columns as c
JOIN sys.types as types
	ON types.user_type_id = c.user_type_id
JOIN sys.tables as t
    ON c.object_id = t.object_id
JOIN sys.schemas as s
    ON t.schema_id = s.schema_id
WHERE s.name = %(schema)s
    AND t.name = %(table)s
    AND c.is_identity = 0
    AND c.is_computed = 0
ORDER BY c.column_id"""

    sql_columns = []
    for import_config in import_configs:
        with conn.cursor() as cursor:
            cursor.execute(get_columns_query, {'schema': import_config.schema, 'table': import_config.table})
            sql_columns.append([SqlMetaColumn(*row) for row in cursor.fetchall()])
    return sql_columns


def quote_identifier(identifier: str) -> str:
    return f"[{identifier.replace(']', ']]')}]"


def normalize_row(row: tuple) -> tuple:
    return tuple(None if pd.isna(value) else value for value in row)


root_path = Path(__file__).resolve().parents[1]
load_dotenv()
import_configs = read_imports(root_path)
validate_import_sources(root_path, import_configs)
validate_excel_sources(root_path, import_configs)
with connect(os.getenv("SQL_CONNECTION_STRING")) as conn:
    validate_target_tables(conn, import_configs)
    sql_columns = get_sql_meta_columns(conn, import_configs)
    for i, import_config in enumerate(import_configs):
        validate_target_columns(root_path, sql_columns[i], import_config)
        validate_excel_data(root_path, sql_columns[i], import_config)

    for i, import_config in enumerate(import_configs):
        import_excel_data(root_path, conn, sql_columns[i], import_config)


print("Done!")