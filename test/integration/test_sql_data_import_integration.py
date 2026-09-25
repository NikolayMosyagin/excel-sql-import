from mssql_python import Connection
import pandas as pd
import pytest

from src.import_config import ImportConfig, ImportMode
from src.import_result import ImportResult
from src.sql_data_import import (
    write_dataframe,
    upsert_dataframe,
    replace_by_columns_dataframe,
)


def test_write_dataframe_appends_rows(sql_connection: Connection, test_table: str):
    with sql_connection.cursor() as cursor:
        cursor.execute(f"INSERT INTO dbo.{test_table} VALUES(100, 'Existing')")
    sql_connection.commit()

    import_config = ImportConfig(
        "test",
        "test.xlsx",
        "sheet1",
        "dbo",
        test_table,
        mode=ImportMode.APPEND
    )

    df = pd.DataFrame({
        "ID": [1, 2],
        "Name": ["First", "Second"]
    })

    import_result = write_dataframe(sql_connection, df, ["ID", "Name"], import_config)

    sql_query = f"""SELECT ID, Name FROM dbo.{test_table} ORDER BY ID"""
    with sql_connection.cursor() as cursor:
        cursor.execute(sql_query)
        result = list(tuple(row) for row in cursor.fetchall())

    assert result == [(1, "First"), (2, "Second"), (100, "Existing")]
    assert import_result == ImportResult(inserted=2)


def test_write_dataframe_appends_rows_across_multiple_batches(
    sql_connection: Connection, 
    test_table: str
):
    import_config = ImportConfig(
        "test",
        "test.xlsx",
        "sheet1",
        "dbo",
        test_table,
        mode=ImportMode.APPEND
    )
    
    df = pd.DataFrame({
        "ID": list(range(2001)),
        "Name": [f"Name{i}" for i in range(2001)]
    })
    
    import_result = write_dataframe(sql_connection, df, ["ID", "Name"], import_config)

    assert import_result == ImportResult(inserted=2001)

    with sql_connection.cursor() as cursor:
        cursor.execute(f"SELECT COUNT(*) FROM dbo.{test_table}")
        result = cursor.fetchone()[0]

    assert result == 2001

    with sql_connection.cursor() as cursor:
        cursor.execute(f"SELECT ID, Name FROM dbo.{test_table} WHERE ID in (0, 999, 1000, 1999, 2000) ORDER BY ID")
        result = [tuple(row) for row in cursor.fetchall()]
    assert result == [
        (0, "Name0"),
        (999, "Name999"),
        (1000, "Name1000"),
        (1999, "Name1999"),
        (2000, "Name2000")
    ]


def test_write_dataframe_replaces_rows(sql_connection: Connection, test_table: str):
    with sql_connection.cursor() as cursor:
        cursor.execute(f"INSERT INTO dbo.{test_table} VALUES(100, 'Existing')")
    sql_connection.commit()
    import_config = ImportConfig(
        "test",
        "test.xlsx",
        "sheet1",
        "dbo",
        test_table,
        mode=ImportMode.REPLACE
    )
    
    df = pd.DataFrame({
        "ID": [1, 2],
        "Name": ["First", "Second"]
    })
    
    import_result = write_dataframe(sql_connection, df, ["ID", "Name"], import_config)

    sql_query = f"""SELECT ID, Name FROM dbo.{test_table} ORDER BY ID"""
    with sql_connection.cursor() as cursor:
        cursor.execute(sql_query)
        result = list(tuple(row) for row in cursor.fetchall())

    assert result == [(1, "First"), (2, "Second")]
    assert import_result == ImportResult(inserted=2, deleted=1)


def test_upsert_dataframe_updates_existing_and_inserts_new_rows(
    sql_connection: Connection, 
    test_table: str
):
    with sql_connection.cursor() as cursor:
        cursor.execute(f"INSERT INTO dbo.{test_table} (ID, Name) VALUES (1, 'name1'), (100, 'name100')")
    sql_connection.commit()
    import_config = ImportConfig(
        "test",
        "test.xlsx",
        "sheet1",
        "dbo",
        test_table,
        mode=ImportMode.UPSERT,
        key_columns=("ID",)
    )
    df = pd.DataFrame({
        "ID": [1, 2],
        "Name": ["First", "Second"]
    })
    import_result = upsert_dataframe(sql_connection, df, ["ID", "Name"], import_config)
    sql_query = f"""SELECT ID, Name FROM dbo.{test_table} ORDER BY ID"""
    with sql_connection.cursor() as cursor:
        cursor.execute(sql_query)
        result = list(tuple(row) for row in cursor.fetchall())

    assert result == [(1, "First"), (2, "Second"), (100, "name100")]
    assert import_result == ImportResult(inserted=1, updated=1)


def test_upsert_dataframe_rejects_multiple_target_matches(
    sql_connection: Connection,
    test_table: str
):
    with sql_connection.cursor() as cursor:
        cursor.execute(f"INSERT INTO dbo.{test_table} (ID, Name) VALUES (1, 'Old1'), (1, 'Old2'), (100, 'keep100')")
    sql_connection.commit()
    import_config = ImportConfig(
        "test",
        "test.xlsx",
        "sheet1",
        "dbo",
        test_table,
        mode=ImportMode.UPSERT,
        key_columns=("ID",)
    )
    df = pd.DataFrame({
        "ID": [1, 2],
        "Name": ["New1", "Second"]
    })
    with pytest.raises(ValueError, match="Each UPSERT key must match at most one target row."):
        upsert_dataframe(sql_connection, df, ["ID", "Name"], import_config)


def test_replace_by_columns_dataframe_replaces_matching_rows(
    sql_connection: Connection,
    test_table: str
):
    with sql_connection.cursor() as cursor:
        cursor.execute(f"INSERT INTO dbo.{test_table} VALUES (1, 'name1'), (100, 'name100')")
    sql_connection.commit()
    import_config = ImportConfig(
        "test",
        "test.xlsx",
        "sheet1",
        "dbo",
        test_table,
        mode=ImportMode.REPLACE_BY_COLUMNS,
        replace_columns=("ID",)
    )
    df = pd.DataFrame({
        "ID": [1, 2],
        "Name": ["First", "Second"]
    })
    import_result = replace_by_columns_dataframe(sql_connection, df, ["ID", "Name"], import_config)

    sql_query = f"""SELECT ID, Name FROM dbo.{test_table} ORDER BY ID"""
    with sql_connection.cursor() as cursor:
        cursor.execute(sql_query)
        result = list(tuple(row) for row in cursor.fetchall())
    
    assert result == [(1, "First"), (2, "Second"), (100, "name100")]
    assert import_result == ImportResult(inserted=2, deleted=1)


def test_replace_by_columns_dataframe_replaces_multiple_matching_rows(
    sql_connection: Connection,
    test_table: str
):
    with sql_connection.cursor() as cursor:
        cursor.execute(f"INSERT INTO dbo.{test_table} VALUES (1, 'Old1'), (1, 'Old2'), (100, 'Keep100')")
    sql_connection.commit()
    import_config = ImportConfig(
        "test",
        "test.xlsx",
        "sheet1",
        "dbo",
        test_table,
        mode=ImportMode.REPLACE_BY_COLUMNS,
        replace_columns=("ID",)
    )
    df = pd.DataFrame({
        "ID": [1, 1, 2],
        "Name": ["New1", "New2", "Second"]
    })
    import_result = replace_by_columns_dataframe(sql_connection, df, ["ID", "Name"], import_config)

    sql_query = f"""SELECT ID, Name FROM dbo.{test_table} ORDER BY ID, Name"""
    with sql_connection.cursor() as cursor:
        cursor.execute(sql_query)
        result = list(tuple(row) for row in cursor.fetchall())
    
    assert result == [
        (1, "New1"), 
        (1, "New2"),
        (2, "Second"),
        (100, "Keep100")
    ]
    assert import_result == ImportResult(inserted=3, deleted=2)


def test_upsert_dataframe_updates_and_inserts_rows_by_composite_key(
    sql_connection: Connection,
    test_composite_table: str,
):
    with sql_connection.cursor() as cursor:
        cursor.execute(f"INSERT INTO dbo.{test_composite_table} VALUES (1, 10, 'OldA'), (1, 20, 'OldB'), (5, 10, 'Keep')")
    sql_connection.commit()
    import_config = ImportConfig(
        "test",
        "test.xlsx",
        "sheet1",
        "dbo",
        test_composite_table,
        mode=ImportMode.UPSERT,
        key_columns=("ID", "Category")
    )
    df = pd.DataFrame({
        "ID": [1, 1],
        "Category": [10, 30],
        "Name": ["NewA", "NewC"]
    })
    import_result = upsert_dataframe(sql_connection, df, ["ID", "Category", "Name"], import_config)

    sql_query = f"SELECT ID, Category, Name FROM dbo.{test_composite_table} ORDER BY ID, Category, Name"
    with sql_connection.cursor() as cursor:
        cursor.execute(sql_query)
        result = list(tuple(row) for row in cursor.fetchall())
    
    assert result == [
        (1, 10, "NewA"), 
        (1, 20, "OldB"),
        (1, 30, "NewC"),
        (5, 10, "Keep"),
    ]
    assert import_result == ImportResult(inserted=1, updated=1)


def test_replace_by_columns_dataframe_replaces_rows_by_composite_columns(
    sql_connection: Connection,
    test_composite_table: str
):
    with sql_connection.cursor() as cursor:
        cursor.execute(
            f"INSERT INTO dbo.{test_composite_table} VALUES "
            "(1, 10, 'OldA'), (1, 20, 'OldB'), (5, 10, 'keepA'), (5, 20, 'keepB')"
        )
    sql_connection.commit()
    import_config = ImportConfig(
        "test",
        "test.xlsx",
        "sheet1",
        "dbo",
        test_composite_table,
        mode=ImportMode.REPLACE_BY_COLUMNS,
        replace_columns=("ID", "Category")
    )
    df = pd.DataFrame({
        "ID": [1, 1, 1, 5],
        "Category": [20, 20, 30, 30],
        "Name": ["NewA", "NewB", "NewC", "NewD"]
    })
    import_result = replace_by_columns_dataframe(sql_connection, df, ["ID", "Category", "Name"], import_config)

    sql_query = f"""SELECT ID, Category, Name FROM dbo.{test_composite_table} ORDER BY ID, Category, Name"""
    with sql_connection.cursor() as cursor:
        cursor.execute(sql_query)
        result = list(tuple(row) for row in cursor.fetchall())
    
    assert result == [
        (1, 10, "OldA"),
        (1, 20, "NewA"),
        (1, 20, "NewB"),
        (1, 30, "NewC"),
        (5, 10, "keepA"),
        (5, 20, "keepB"),
        (5, 30, "NewD")
    ]
    assert import_result == ImportResult(inserted=4, deleted=1)