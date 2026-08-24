from mssql_python import Connection

from src.import_config import ImportConfig
from src.sql_meta_column import SqlMetaColumn


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