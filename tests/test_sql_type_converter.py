"""Unit tests for sql_type_converter.py – physicalType pass-through and maxLength support."""

import pytest
from open_data_contract_standard.model import SchemaProperty

from datacontract.export.sql_type_converter import (
    _get_max_length,
    convert_to_duckdb,
    convert_to_snowflake,
    convert_to_sql_type,
    convert_type_to_postgres,
    convert_type_to_sqlserver,
    convert_type_to_trino,
)


# ---------------------------------------------------------------------------
# _get_max_length helper
# ---------------------------------------------------------------------------


def test_get_max_length_from_logical_type_options():
    field = SchemaProperty(logicalType="string", logicalTypeOptions={"maxLength": 255})
    assert _get_max_length(field) == 255


def test_get_max_length_none_when_absent():
    field = SchemaProperty(logicalType="string")
    assert _get_max_length(field) is None


# ---------------------------------------------------------------------------
# physicalType pass-through in convert_to_sql_type
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "physical_type,server_type",
    [
        ("VARCHAR(255)", "postgres"),
        ("VARCHAR(255)", "snowflake"),
        ("VARCHAR(255)", "sqlserver"),
        ("NVARCHAR(100)", "sqlserver"),
        ("CHAR(10)", "postgres"),
        ("DECIMAL(10,2)", "postgres"),
        ("DECIMAL(10,2)", "snowflake"),
        ("varchar(18)", "postgres"),
    ],
)
def test_physical_type_passed_through_as_is(physical_type, server_type):
    """When physicalType is explicitly set it must be returned verbatim regardless of dialect."""
    field = SchemaProperty(logicalType="string", physicalType=physical_type)
    assert convert_to_sql_type(field, server_type) == physical_type


# ---------------------------------------------------------------------------
# Postgres converter – maxLength support
# ---------------------------------------------------------------------------


def test_postgres_string_with_max_length():
    field = SchemaProperty(logicalType="string", logicalTypeOptions={"maxLength": 100})
    assert convert_type_to_postgres(field) == "varchar(100)"


def test_postgres_varchar_with_max_length():
    field = SchemaProperty(logicalType="varchar", logicalTypeOptions={"maxLength": 50})
    assert convert_type_to_postgres(field) == "varchar(50)"


def test_postgres_string_without_max_length():
    field = SchemaProperty(logicalType="string")
    assert convert_type_to_postgres(field) == "text"


def test_postgres_string_uuid_format_ignores_max_length():
    """uuid format takes precedence over maxLength."""
    field = SchemaProperty(logicalType="string", logicalTypeOptions={"format": "uuid", "maxLength": 36})
    assert convert_type_to_postgres(field) == "uuid"


# ---------------------------------------------------------------------------
# Snowflake converter – maxLength support
# ---------------------------------------------------------------------------


def test_snowflake_string_with_max_length():
    field = SchemaProperty(logicalType="string", logicalTypeOptions={"maxLength": 200})
    assert convert_to_snowflake(field) == "varchar(200)"


def test_snowflake_string_without_max_length():
    field = SchemaProperty(logicalType="string")
    assert convert_to_snowflake(field) == "STRING"


# ---------------------------------------------------------------------------
# SQL Server converter – maxLength support
# ---------------------------------------------------------------------------


def test_sqlserver_string_with_max_length():
    field = SchemaProperty(logicalType="string", logicalTypeOptions={"maxLength": 128})
    assert convert_type_to_sqlserver(field) == "varchar(128)"


def test_sqlserver_string_without_max_length():
    field = SchemaProperty(logicalType="string")
    assert convert_type_to_sqlserver(field) == "varchar"


# ---------------------------------------------------------------------------
# DuckDB converter – maxLength support
# ---------------------------------------------------------------------------


def test_duckdb_string_with_max_length():
    field = SchemaProperty(logicalType="string", logicalTypeOptions={"maxLength": 64})
    assert convert_to_duckdb(field) == "VARCHAR(64)"


def test_duckdb_string_without_max_length():
    field = SchemaProperty(logicalType="string")
    assert convert_to_duckdb(field) == "VARCHAR"


# ---------------------------------------------------------------------------
# Trino converter – maxLength support
# ---------------------------------------------------------------------------


def test_trino_string_with_max_length():
    field = SchemaProperty(logicalType="string", logicalTypeOptions={"maxLength": 512})
    assert convert_type_to_trino(field) == "varchar(512)"


def test_trino_string_without_max_length():
    field = SchemaProperty(logicalType="string")
    assert convert_type_to_trino(field) == "varchar"


# ---------------------------------------------------------------------------
# Existing non-string types are unaffected
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "logical_type,expected",
    [
        ("integer", "integer"),
        ("boolean", "boolean"),
        ("date", "date"),
        ("timestamp", "timestamptz"),
    ],
)
def test_postgres_non_string_types_unchanged(logical_type, expected):
    field = SchemaProperty(logicalType=logical_type)
    assert convert_type_to_postgres(field) == expected
