from datetime import datetime
from decimal import Decimal
import math

import pandas as pd

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

        if not math.isfinite(value):
            raise ValueError(
                f"Column '{sql_column.name}', row {excel_row}: "
                f"expected a finite number, but got '{value}'."
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
    for index, value in series.items():
        excel_row = index + 2

        if type(value) not in (int, float):
            raise ValueError(
                f"Column '{sql_column.name}', row {excel_row}: "
                f"expected a numeric value, but got '{value}' "
                f"of type '{type(value).__name__}'."
            )

        if not math.isfinite(value):
            raise ValueError(
                f"Column '{sql_column.name}', row {excel_row}: "
                f"expected a finite number, but got '{value}'."
            )
        
        min_value, max_value = (
            (2.23E-308, 1.79E+308)
            if sql_column.type_name == 'float' and sql_column.precision >= 25 else
            (1.18E-38, 3.40E+38)
        )

        if value != 0 and (abs(value) < min_value or abs(value) > max_value):
            raise ValueError(
                f"Column '{sql_column.name}', row {excel_row}: "
                f"absolute value must be between {min_value} and {max_value}, or equal to 0, but got {abs(value)}."
            ) 


def validate_datetime_values(sql_column: SqlMetaColumn, series: pd.Series) -> None:
    for index, value in series.items():
        excel_row = index + 2

        if not isinstance(value, datetime):
            raise ValueError(
                f"Column '{sql_column.name}', row {excel_row}: "
                f"expected a datetime value, but got '{value}' "
                f"of type '{type(value).__name__}'."
            )

        min_date, max_date = datetime(1753, 1, 1), datetime(9999, 12, 31, 23, 59, 59, 997000)
        if value < min_date or value > max_date:
            raise ValueError(
                f"Column '{sql_column.name}', row {excel_row}: "
                f"value '{value}' is outside the supported range for SQL type 'datetime' "
                f"(1753-01-01 00:00:00.000 through 9999-12-31 23:59:59.997)."
            )
        
        if (value.microsecond % 10000) not in (0, 3000, 7000):
            raise ValueError(
                f"Column '{sql_column.name}', row {excel_row}: "
                f"value '{value}' does not fit SQL type 'datetime': "
                f"fractional seconds must match the supported precision "
                f"(.000, .003, .007, .010, .013, .017, ...)."
            )


def validate_datetime2_values(sql_column: SqlMetaColumn, series: pd.Series) -> None:
    for index, value in series.items():
        excel_row = index + 2

        if not isinstance(value, datetime):
            raise ValueError(
                f"Column '{sql_column.name}', row {excel_row}: "
                f"expected a datetime value, but got '{value}' "
                f"of type '{type(value).__name__}'."
            )

        if sql_column.scale < 6 and value.microsecond % (10 ** (6 - sql_column.scale)) > 0:
            raise ValueError(
                f"Column '{sql_column.name}', row {excel_row}: "
                f"value '{value}' does not fit SQL type 'datetime2({sql_column.scale})': "
                f"fractional seconds exceed the supported precision."
            )


def validate_smalldatetime_values(sql_column: SqlMetaColumn, series: pd.Series) -> None:
    for index, value in series.items():
        excel_row = index + 2

        if not isinstance(value, datetime):
            raise ValueError(
                f"Column '{sql_column.name}', row {excel_row}: "
                f"expected a datetime value, but got '{value}' "
                f"of type '{type(value).__name__}'."
            )

        min_date, max_date = datetime(1900, 1, 1, 0, 0), datetime(2079, 6, 6, 23, 59)
        if value < min_date or value > max_date:
            raise ValueError(
                f"Column '{sql_column.name}', row {excel_row}: "
                f"value '{value}' is outside the supported range for SQL type 'smalldatetime' "
                f"(1900-01-01 through 2079-06-06)."
            )
        
        if value.second > 0 or value.microsecond > 0:
            raise ValueError(
                f"Column '{sql_column.name}', row {excel_row}: "
                f"value '{value}' does not fit SQL type 'smalldatetime': "
                f"seconds and fractional seconds must be zero."
            )


def validate_date_values(sql_column: SqlMetaColumn, series: pd.Series) -> None:
    for index, value in series.items():
        excel_row = index + 2

        if not isinstance(value, datetime):
            raise ValueError(
                f"Column '{sql_column.name}', row {excel_row}: "
                f"expected a date value, but got '{value}' "
                f"of type '{type(value).__name__}'."
            )

        if value.hour > 0 or value.minute > 0 or value.second > 0 or value.microsecond > 0:
            raise ValueError(
                f"Column '{sql_column.name}', row {excel_row}: "
                f"value must not contain a time component for SQL type 'date', "
                f"but got '{value}'.    "
            )


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

    "date": validate_date_values,
    "datetime": validate_datetime_values,
    "datetime2": validate_datetime2_values,
    "smalldatetime": validate_smalldatetime_values
}

MINMAX_VALUE_BY_SQL_TYPE = {
    "tinyint": (0, 2**8 - 1),
    "smallint": (-2**15, 2**15 - 1),
    "int": (-2**31, 2**31 - 1),
    "bigint": (-2**63, 2**63 - 1)
}
