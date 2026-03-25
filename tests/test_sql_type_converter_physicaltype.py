"""
Tests for SQL type converter handling of parameterized physicalType values.
Covers issue #1086: physicalType with precision/length constraints (e.g. VARCHAR(255),
DECIMAL(10,2)) must be translated through the server-specific converter rather than
returned verbatim or discarded.
"""

import pytest
from open_data_contract_standard.model import SchemaProperty

from datacontract.export.sql_type_converter import (
    convert_to_sql_type,
    _extract_base_type,
    _extract_params,
)


# ---------------------------------------------------------------------------
# _extract_base_type helper
# ---------------------------------------------------------------------------


def test_extract_base_type_parameterized():
    assert _extract_base_type("VARCHAR(255)") == "VARCHAR"


def test_extract_base_type_decimal():
    assert _extract_base_type("DECIMAL(10,2)") == "DECIMAL"


def test_extract_base_type_no_params():
    assert _extract_base_type("TEXT") == "TEXT"


# ---------------------------------------------------------------------------
# _extract_params helper
# ---------------------------------------------------------------------------


def test_extract_params_single():
    assert _extract_params("VARCHAR(255)") == "255"


def test_extract_params_multiple():
    assert _extract_params("DECIMAL(10,2)") == "10,2"


def test_extract_params_no_params():
    assert _extract_params("TEXT") is None


# ---------------------------------------------------------------------------
# convert_to_sql_type: bare (non-parameterized) physicalType still routes
# to the server-specific converter.
# ---------------------------------------------------------------------------


def test_bare_varchar_physicaltype_postgres():
    """A bare physicalType like 'varchar' (no parens) goes through the postgres converter."""
    field = SchemaProperty(name="col", physicalType="varchar")
    result = convert_to_sql_type(field, "postgres")
    # The postgres converter maps "varchar" -> "text"
    assert result == "text"


def test_bare_string_logicaltype_postgres():
    """logicalType='string' with no physicalType is still converted correctly."""
    field = SchemaProperty(name="col", logicalType="string")
    result = convert_to_sql_type(field, "postgres")
    assert result == "text"


# ---------------------------------------------------------------------------
# convert_to_sql_type: parameterized physicalType is translated through the
# server-specific converter and parameters are preserved where the target
# type supports them.
# ---------------------------------------------------------------------------


def test_varchar_255_postgres():
    """VARCHAR(255) physicalType on postgres: base 'varchar' -> 'text', text doesn't accept
    params on postgres, so result is 'text' (no params)."""
    field = SchemaProperty(name="col", physicalType="VARCHAR(255)")
    result = convert_to_sql_type(field, "postgres")
    assert result == "text"


def test_varchar_255_snowflake():
    """VARCHAR(255) on snowflake: 'varchar' -> 'VARCHAR', and VARCHAR accepts params -> 'VARCHAR(255)'."""
    field = SchemaProperty(name="col", physicalType="VARCHAR(255)")
    result = convert_to_sql_type(field, "snowflake")
    assert result == "VARCHAR(255)"


def test_varchar_255_sqlserver():
    """VARCHAR(255) on sqlserver: 'varchar' -> 'varchar', varchar accepts params -> 'varchar(255)'."""
    field = SchemaProperty(name="col", physicalType="VARCHAR(255)")
    result = convert_to_sql_type(field, "sqlserver")
    assert result == "varchar(255)"


def test_decimal_precision_snowflake():
    """DECIMAL(10,2) on snowflake: 'decimal' -> 'NUMBER', and NUMBER accepts params -> 'NUMBER(10,2)'."""
    field = SchemaProperty(name="price", physicalType="DECIMAL(10,2)")
    result = convert_to_sql_type(field, "snowflake")
    assert result == "NUMBER(10,2)"


def test_decimal_precision_postgres():
    """DECIMAL(10,2) on postgres: 'decimal' -> 'decimal', decimal accepts params -> 'decimal(10,2)'."""
    field = SchemaProperty(name="price", physicalType="DECIMAL(10,2)")
    result = convert_to_sql_type(field, "postgres")
    assert result == "decimal(10,2)"


def test_nvarchar_50_postgres():
    """NVARCHAR(50) on postgres: postgres has no NVARCHAR type. The converter returns None
    for unknown base types -> fallback to verbatim 'NVARCHAR(50)'."""
    field = SchemaProperty(name="col", physicalType="NVARCHAR(50)")
    result = convert_to_sql_type(field, "postgres")
    # nvarchar is not in the postgres converter's mapping -> fallback verbatim
    assert result == "NVARCHAR(50)"


def test_nvarchar_500_sqlserver():
    """NVARCHAR(500) on sqlserver: 'nvarchar' is not in the sqlserver converter's explicit mapping
    (converter returns None), so we fall back to verbatim 'NVARCHAR(500)'.
    NVARCHAR is a valid SQL Server type so verbatim is the right answer here."""
    field = SchemaProperty(name="col", physicalType="NVARCHAR(500)")
    result = convert_to_sql_type(field, "sqlserver")
    assert result == "NVARCHAR(500)"


def test_float_24_postgres():
    """FLOAT(24) on postgres: 'float' -> 'real', real does NOT accept params on postgres
    -> result is 'real' (params stripped)."""
    field = SchemaProperty(name="col", physicalType="FLOAT(24)")
    result = convert_to_sql_type(field, "postgres")
    assert result == "real"


def test_numeric_18_4_postgres():
    """NUMERIC(18,4) on postgres: 'numeric' -> 'numeric', numeric accepts params -> 'numeric(18,4)'."""
    field = SchemaProperty(name="col", physicalType="NUMERIC(18,4)")
    result = convert_to_sql_type(field, "postgres")
    assert result == "numeric(18,4)"


def test_char_10_snowflake():
    """CHAR(10) on snowflake: 'char' is unknown in snowflake converter -> None -> fallback verbatim."""
    field = SchemaProperty(name="col", physicalType="CHAR(10)")
    result = convert_to_sql_type(field, "snowflake")
    # snowflake converter doesn't handle 'char' explicitly -> returns None -> fallback verbatim
    assert result == "CHAR(10)"


def test_char_10_sqlserver():
    """CHAR(10) on sqlserver: not mapped explicitly -> fallback verbatim."""
    field = SchemaProperty(name="col", physicalType="CHAR(10)")
    result = convert_to_sql_type(field, "sqlserver")
    assert result == "CHAR(10)"


def test_varchar_255_not_none_postgres():
    """Regression: VARCHAR(255) must NOT return None from the postgres converter path."""
    field = SchemaProperty(name="amount", physicalType="VARCHAR(255)")
    result = convert_to_sql_type(field, "postgres")
    assert result is not None


def test_decimal_precision_not_none_snowflake():
    """Regression: DECIMAL(10,2) must NOT return None from the snowflake converter path."""
    field = SchemaProperty(name="price", physicalType="DECIMAL(10,2)")
    result = convert_to_sql_type(field, "snowflake")
    assert result is not None
