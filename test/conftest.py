from dotenv import load_dotenv
import os
from pathlib import Path

import pytest
from mssql_python import connect, Connection


@pytest.fixture
def test_sql_connection_str() -> str:
    app_dir = Path(__file__).resolve().parents[1]
    load_dotenv(app_dir / ".env")
    sql_connection_str = os.getenv("TEST_SQL_CONNECTION_STRING")
    if not sql_connection_str:
        raise RuntimeError("TEST_SQL_CONNECTION_STRING is not set.")
    return sql_connection_str


@pytest.fixture
def sql_connection(test_sql_connection_str: str):

    conn = connect(test_sql_connection_str)

    yield conn

    conn.close()


@pytest.fixture
def test_table(sql_connection: Connection):
    table_name = "test_table"

    drop_table_query = f"DROP TABLE IF EXISTS dbo.{table_name}"
    with sql_connection.cursor() as cursor:
        cursor.execute(drop_table_query)
        cursor.execute(f"""
            CREATE TABLE dbo.{table_name}(
                ID int NOT NULL,
                Name nvarchar(100) NULL
            )
        """)
    sql_connection.commit()

    try:
        yield table_name
    finally:
        sql_connection.rollback()
        with sql_connection.cursor() as cursor:
            cursor.execute(drop_table_query)
        sql_connection.commit()


@pytest.fixture
def test_composite_table(sql_connection: Connection):
    table_name = "test_composite_table"

    drop_table_query = f"DROP TABLE IF EXISTS dbo.{table_name}"
    with sql_connection.cursor() as cursor:
        cursor.execute(drop_table_query)
        cursor.execute(f"""
            CREATE TABLE dbo.{table_name}(
                ID int NOT NULL,
                Category int NOT NULL,
                Name nvarchar(100) NULL
            )
        """)
    sql_connection.commit()
    try:
        yield table_name
    finally:
        sql_connection.rollback()
        with sql_connection.cursor() as cursor:
            cursor.execute(drop_table_query)
        sql_connection.commit()