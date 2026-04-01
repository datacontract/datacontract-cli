"""
Tests for SQL type converter handling of parameterized physicalType values
and comprehensive type coverage across all server types.
"""

from open_data_contract_standard.model import SchemaProperty

from datacontract.export.sql_type_converter import (
    _get_type,
    convert_to_sql_type,
)

# ---------------------------------------------------------------------------
# _get_type helper
# ---------------------------------------------------------------------------


def test_get_type_parameterized():
    field = SchemaProperty(name="col", physicalType="VARCHAR(255)")
    assert _get_type(field) == "VARCHAR(255)"


def test_get_type_decimal():
    field = SchemaProperty(name="col", physicalType="DECIMAL(10,2)")
    assert _get_type(field) == "DECIMAL(10,2)"


def test_get_type_no_params():
    field = SchemaProperty(name="col", physicalType="TEXT")
    assert _get_type(field) == "TEXT"


def test_get_type_prefers_physical_type():
    field = SchemaProperty(name="col", physicalType="VARCHAR(255)", logicalType="string")
    assert _get_type(field) == "VARCHAR(255)"


def test_get_type_falls_back_to_logical_type():
    field = SchemaProperty(name="col", logicalType="string")
    assert _get_type(field) == "string"


def test_get_type_none_when_empty():
    field = SchemaProperty(name="col")
    assert _get_type(field) is None


# ---------------------------------------------------------------------------
# convert_to_sql_type: bare (non-parameterized) physicalType still routes
# to the server-specific converter.
# ---------------------------------------------------------------------------


def test_bare_varchar_physicaltype_postgres():
    """A bare physicalType like 'varchar' (no parens) goes through the postgres converter."""
    field = SchemaProperty(name="col", physicalType="varchar")
    result = convert_to_sql_type(field, "postgres")
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
    """NVARCHAR(50) on postgres: nvarchar maps to 'text', which doesn't accept params -> 'text'."""
    field = SchemaProperty(name="col", physicalType="NVARCHAR(50)")
    result = convert_to_sql_type(field, "postgres")
    assert result == "text"


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
    assert result == "CHAR(10)"


def test_char_10_sqlserver():
    """CHAR(10) on sqlserver: not mapped explicitly -> fallback verbatim."""
    field = SchemaProperty(name="col", physicalType="CHAR(10)")
    result = convert_to_sql_type(field, "sqlserver")
    assert result == "CHAR(10)"


def test_varchar_255_mysql():
    """VARCHAR(255) on mysql: 'varchar' -> 'varchar', accepts params -> 'varchar(255)'."""
    field = SchemaProperty(name="col", physicalType="VARCHAR(255)")
    result = convert_to_sql_type(field, "mysql")
    assert result == "varchar(255)"


def test_decimal_10_2_mysql():
    """DECIMAL(10,2) on mysql: 'decimal' -> 'decimal', accepts params -> 'decimal(10,2)'."""
    field = SchemaProperty(name="price", physicalType="DECIMAL(10,2)")
    result = convert_to_sql_type(field, "mysql")
    assert result == "decimal(10,2)"


def test_float_24_mysql():
    """FLOAT(24) on mysql: 'float' -> 'float', accepts params -> 'float(24)'."""
    field = SchemaProperty(name="col", physicalType="FLOAT(24)")
    result = convert_to_sql_type(field, "mysql")
    assert result == "float(24)"


def test_decimal_10_2_bigquery():
    """DECIMAL(10,2) on bigquery: 'decimal' -> 'NUMERIC', accepts params -> 'NUMERIC(10,2)'."""
    field = SchemaProperty(name="price", physicalType="DECIMAL(10,2)")
    result = convert_to_sql_type(field, "bigquery")
    assert result == "NUMERIC(10,2)"


def test_varchar_100_databricks():
    """VARCHAR(100) on databricks: 'varchar' -> 'STRING'."""
    field = SchemaProperty(name="col", physicalType="VARCHAR(100)")
    result = convert_to_sql_type(field, "databricks")
    assert result == "STRING"


def test_decimal_18_4_trino():
    """DECIMAL(18,4) on trino: 'decimal' -> 'decimal', accepts params -> 'decimal(18,4)'."""
    field = SchemaProperty(name="col", physicalType="DECIMAL(18,4)")
    result = convert_to_sql_type(field, "trino")
    assert result == "decimal(18,4)"


def test_varchar_255_local_duckdb():
    """VARCHAR(255) on local (DuckDB): 'varchar' -> 'VARCHAR', accepts params -> 'VARCHAR(255)'."""
    field = SchemaProperty(name="col", physicalType="VARCHAR(255)")
    result = convert_to_sql_type(field, "local")
    assert result == "VARCHAR(255)"


def test_number_10_2_oracle():
    """NUMBER(10,2) on oracle: physicalType returned verbatim by oracle converter."""
    field = SchemaProperty(name="col", physicalType="NUMBER(10,2)")
    result = convert_to_sql_type(field, "oracle")
    assert result == "NUMBER(10,2)"


# ---------------------------------------------------------------------------
# Compound types
# ---------------------------------------------------------------------------


def test_compound_timestamp_with_timezone():
    """TIMESTAMP(6) WITH TIME ZONE is valid postgres SQL and should pass through verbatim."""
    field = SchemaProperty(name="col", physicalType="TIMESTAMP(6) WITH TIME ZONE")
    result = convert_to_sql_type(field, "postgres")
    assert result == "TIMESTAMP(6) WITH TIME ZONE"


def test_compound_interval_passthrough():
    """INTERVAL DAY(2) TO SECOND(6) passes through verbatim."""
    field = SchemaProperty(name="col", physicalType="INTERVAL DAY(2) TO SECOND(6)")
    result = convert_to_sql_type(field, "oracle")
    assert result == "INTERVAL DAY(2) TO SECOND(6)"


# ---------------------------------------------------------------------------
# Logical type mapping: spot-check that each server maps common types to
# the correct SQL type (not just non-None).
# ---------------------------------------------------------------------------


def test_logical_string_snowflake():
    field = SchemaProperty(name="col", logicalType="string")
    assert convert_to_sql_type(field, "snowflake") == "STRING"


def test_logical_timestamp_postgres():
    field = SchemaProperty(name="col", logicalType="timestamp")
    assert convert_to_sql_type(field, "postgres") == "timestamptz"


def test_logical_boolean_mysql():
    field = SchemaProperty(name="col", logicalType="boolean")
    assert convert_to_sql_type(field, "mysql") == "boolean"


def test_logical_date_bigquery():
    field = SchemaProperty(name="col", logicalType="date")
    assert convert_to_sql_type(field, "bigquery") == "DATE"


def test_logical_integer_sqlserver():
    field = SchemaProperty(name="col", logicalType="integer")
    assert convert_to_sql_type(field, "sqlserver") == "INT"


def test_logical_double_trino():
    field = SchemaProperty(name="col", logicalType="double")
    assert convert_to_sql_type(field, "trino") == "double"


def test_logical_bytes_oracle():
    field = SchemaProperty(name="col", logicalType="bytes")
    assert convert_to_sql_type(field, "oracle") == "RAW(2000)"


def test_logical_time_databricks():
    field = SchemaProperty(name="col", logicalType="time")
    assert convert_to_sql_type(field, "databricks") == "STRING"


def test_logical_decimal_local():
    field = SchemaProperty(name="col", logicalType="decimal")
    assert convert_to_sql_type(field, "local") == "decimal"


def test_logical_long_s3():
    field = SchemaProperty(name="col", logicalType="long")
    assert convert_to_sql_type(field, "s3") == "BIGINT"


def test_logical_float_dataframe():
    field = SchemaProperty(name="col", logicalType="float")
    assert convert_to_sql_type(field, "dataframe") == "FLOAT"
