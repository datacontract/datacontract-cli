"""
Tests for SQL type converter handling of parameterized physicalType values.
Covers issue #1086: physicalType with precision/length constraints (e.g. VARCHAR(255),
DECIMAL(10,2)) must be passed through unchanged instead of failing per-server type lookup.
"""

import pytest
from open_data_contract_standard.model import SchemaProperty

from datacontract.export.sql_type_converter import (
    convert_to_sql_type,
    _extract_base_type,
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
# convert_to_sql_type: parameterized physicalType passed through unchanged
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "physical_type",
    [
        "VARCHAR(255)",
        "varchar(255)",
        "DECIMAL(10,2)",
        "NUMERIC(18,4)",
        "CHAR(10)",
        "NVARCHAR(500)",
        "FLOAT(24)",
    ],
)
@pytest.mark.parametrize(
    "server_type",
    ["postgres", "snowflake", "databricks", "bigquery", "trino", "sqlserver", "local", "s3"],
)
def test_parameterized_physicaltype_passes_through(physical_type, server_type):
    """Parameterized physicalType values must be returned verbatim for all server types."""
    field = SchemaProperty(name="col", physicalType=physical_type)
    result = convert_to_sql_type(field, server_type)
    assert result == physical_type, (
        f"Expected physicalType '{physical_type}' to be returned unchanged for server "
        f"'{server_type}', got '{result}'"
    )


# ---------------------------------------------------------------------------
# convert_to_sql_type: non-parameterized physicalType still routed to converter
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


def test_varchar_255_not_none_postgres():
    """Regression: VARCHAR(255) must NOT return None from the postgres converter path."""
    field = SchemaProperty(name="amount", physicalType="VARCHAR(255)")
    result = convert_to_sql_type(field, "postgres")
    assert result is not None
    assert result == "VARCHAR(255)"


def test_decimal_precision_not_none_snowflake():
    """Regression: DECIMAL(10,2) must NOT return None from the snowflake converter path."""
    field = SchemaProperty(name="price", physicalType="DECIMAL(10,2)")
    result = convert_to_sql_type(field, "snowflake")
    assert result is not None
    assert result == "DECIMAL(10,2)"
