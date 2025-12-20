"""Unit tests for sql_importer helper functions.

Tests individual functions and helper methods in the sql_importer module,
focusing on isolated unit testing with no external dependencies.
"""

import pytest
import sqlglot
from sqlglot.dialects.dialect import Dialects
from sqlglot.expressions import ColumnDef

from datacontract.imports.sql_importer import (
    get_description,
    get_max_length,
    get_precision_scale,
    get_primary_key,
    map_type_from_sql,
    read_file,
    to_col_type,
    to_col_type_normalized,
    to_dialect,
    to_server_type,
)
from datacontract.model.exceptions import DataContractException


class TestToDialect:
    """Test dialect string to SQLGlot dialect conversion."""

    def test_to_dialect_with_none(self):
        """Should return None when input is None."""
        assert to_dialect(None) is None

    def test_to_dialect_with_sqlserver(self):
        """Should convert 'sqlserver' to TSQL dialect."""
        result = to_dialect("sqlserver")
        assert result == Dialects.TSQL

    def test_to_dialect_with_uppercase(self):
        """Should convert uppercase dialect names."""
        result = to_dialect("POSTGRES")
        assert result == Dialects.POSTGRES

    def test_to_dialect_with_lowercase(self):
        """Should convert lowercase dialect names."""
        result = to_dialect("postgres")
        assert result == Dialects.POSTGRES

    def test_to_dialect_with_mixed_case(self):
        """Should convert mixed case dialect names."""
        result = to_dialect("BigQuery")
        assert result == Dialects.BIGQUERY

    def test_to_dialect_with_unrecognized_dialect(self, caplog):
        """Should return None and log warning for unrecognized dialects."""
        result = to_dialect("unknown_dialect")
        assert result is None
        assert "not recognized" in caplog.text


class TestToServerType:
    """Test SQLGlot dialect to server type conversion."""

    def test_to_server_type_tsql(self):
        """Should map TSQL dialect to sqlserver."""
        assert to_server_type(Dialects.TSQL) == "sqlserver"

    def test_to_server_type_postgres(self):
        """Should map POSTGRES dialect to postgres."""
        assert to_server_type(Dialects.POSTGRES) == "postgres"

    def test_to_server_type_bigquery(self):
        """Should map BIGQUERY dialect to bigquery."""
        assert to_server_type(Dialects.BIGQUERY) == "bigquery"

    def test_to_server_type_snowflake(self):
        """Should map SNOWFLAKE dialect to snowflake."""
        assert to_server_type(Dialects.SNOWFLAKE) == "snowflake"

    def test_to_server_type_redshift(self):
        """Should map REDSHIFT dialect to redshift."""
        assert to_server_type(Dialects.REDSHIFT) == "redshift"

    def test_to_server_type_oracle(self):
        """Should map ORACLE dialect to oracle."""
        assert to_server_type(Dialects.ORACLE) == "oracle"

    def test_to_server_type_mysql(self):
        """Should map MYSQL dialect to mysql."""
        assert to_server_type(Dialects.MYSQL) == "mysql"

    def test_to_server_type_databricks(self):
        """Should map DATABRICKS dialect to databricks."""
        assert to_server_type(Dialects.DATABRICKS) == "databricks"

    def test_to_server_type_teradata(self):
        """Should map TERADATA dialect to teradata."""
        assert to_server_type(Dialects.TERADATA) == "teradata"

    def test_to_server_type_unmapped_dialect(self, caplog):
        """Should return None and log warning for unmapped dialects."""
        result = to_server_type(Dialects.SPARK)
        assert result is None
        assert "No server type mapping" in caplog.text


class TestGetPrimaryKey:
    """Test primary key detection in column definitions."""

    def test_get_primary_key_with_primary_key_constraint(self):
        """Should detect PrimaryKeyColumnConstraint."""
        sql = "CREATE TABLE t (id INT PRIMARY KEY)"
        parsed = sqlglot.parse_one(sql, read="postgres")
        column = next(iter(parsed.find_all(ColumnDef)))
        assert get_primary_key(column) is True

    def test_get_primary_key_without_constraint(self):
        """Should return False when no primary key constraint."""
        sql = "CREATE TABLE t (id INT)"
        parsed = sqlglot.parse_one(sql, read="postgres")
        column = next(iter(parsed.find_all(ColumnDef)))
        assert get_primary_key(column) is False

    def test_get_primary_key_with_not_null(self):
        """Should not confuse NOT NULL with PRIMARY KEY."""
        sql = "CREATE TABLE t (id INT NOT NULL)"
        parsed = sqlglot.parse_one(sql, read="postgres")
        column = next(iter(parsed.find_all(ColumnDef)))
        assert get_primary_key(column) is False


class TestToColType:
    """Test column type extraction."""

    def test_to_col_type_integer(self):
        """Should extract integer type."""
        sql = "CREATE TABLE t (id INT)"
        parsed = sqlglot.parse_one(sql, read="postgres")
        column = next(iter(parsed.find_all(ColumnDef)))
        col_type = to_col_type(column, Dialects.POSTGRES)
        assert col_type == "INT"

    def test_to_col_type_varchar(self):
        """Should extract varchar type with length."""
        sql = "CREATE TABLE t (name VARCHAR(100))"
        parsed = sqlglot.parse_one(sql, read="postgres")
        column = next(iter(parsed.find_all(ColumnDef)))
        col_type = to_col_type(column, Dialects.POSTGRES)
        assert col_type is not None
        assert "VARCHAR" in col_type

    def test_to_col_type_decimal_with_precision(self):
        """Should extract decimal type with precision and scale."""
        sql = "CREATE TABLE t (amount DECIMAL(10, 2))"
        parsed = sqlglot.parse_one(sql, read="postgres")
        column = next(iter(parsed.find_all(ColumnDef)))
        col_type = to_col_type(column, Dialects.POSTGRES)
        assert col_type is not None
        assert "DECIMAL" in col_type

    def test_to_col_type_with_dialect_conversion(self):
        """Should use dialect for type conversion."""
        sql = "CREATE TABLE t (data NVARCHAR(50))"
        parsed = sqlglot.parse_one(sql, read="tsql")
        column = next(iter(parsed.find_all(ColumnDef)))
        col_type = to_col_type(column, Dialects.TSQL)
        assert col_type is not None


class TestToColTypeNormalized:
    """Test normalized column type extraction."""

    def test_to_col_type_normalized_int(self):
        """Should normalize INT to lowercase."""
        sql = "CREATE TABLE t (id INT)"
        parsed = sqlglot.parse_one(sql, read="postgres")
        column = next(iter(parsed.find_all(ColumnDef)))
        col_type = to_col_type_normalized(column)
        assert col_type == "int"

    def test_to_col_type_normalized_varchar(self):
        """Should normalize VARCHAR to lowercase."""
        sql = "CREATE TABLE t (name VARCHAR(100))"
        parsed = sqlglot.parse_one(sql, read="postgres")
        column = next(iter(parsed.find_all(ColumnDef)))
        col_type = to_col_type_normalized(column)
        assert col_type == "varchar"

    def test_to_col_type_normalized_decimal(self):
        """Should normalize DECIMAL to lowercase."""
        sql = "CREATE TABLE t (amount DECIMAL(10, 2))"
        parsed = sqlglot.parse_one(sql, read="postgres")
        column = next(iter(parsed.find_all(ColumnDef)))
        col_type = to_col_type_normalized(column)
        assert col_type == "decimal"


class TestGetDescription:
    """Test description extraction from column comments."""

    def test_get_description_without_comment(self):
        """Should return None when no comment present."""
        sql = "CREATE TABLE t (id INT)"
        parsed = sqlglot.parse_one(sql, read="postgres")
        column = next(iter(parsed.find_all(ColumnDef)))
        description = get_description(column)
        assert description is None

    def test_get_description_with_none_comments(self):
        """Should handle columns with no comments gracefully."""
        sql = "CREATE TABLE t (name VARCHAR(100), age INT)"
        parsed = sqlglot.parse_one(sql, read="postgres")
        columns = list(parsed.find_all(ColumnDef))
        # Both columns should have no description
        for column in columns:
            description = get_description(column)
            assert description is None


class TestGetMaxLength:
    """Test maximum length extraction from varchar/char types."""

    def test_get_max_length_varchar_with_length(self):
        """Should extract max length from VARCHAR."""
        sql = "CREATE TABLE t (name VARCHAR(100))"
        parsed = sqlglot.parse_one(sql, read="postgres")
        column = next(iter(parsed.find_all(ColumnDef)))
        max_length = get_max_length(column)
        assert max_length == 100

    def test_get_max_length_char_with_length(self):
        """Should extract max length from CHAR."""
        sql = "CREATE TABLE t (code CHAR(10))"
        parsed = sqlglot.parse_one(sql, read="postgres")
        column = next(iter(parsed.find_all(ColumnDef)))
        max_length = get_max_length(column)
        assert max_length == 10

    def test_get_max_length_nvarchar(self):
        """Should extract max length from NVARCHAR."""
        sql = "CREATE TABLE t (text NVARCHAR(255))"
        parsed = sqlglot.parse_one(sql, read="tsql")
        column = next(iter(parsed.find_all(ColumnDef)))
        max_length = get_max_length(column)
        assert max_length == 255

    def test_get_max_length_nchar(self):
        """Should extract max length from NCHAR."""
        sql = "CREATE TABLE t (code NCHAR(5))"
        parsed = sqlglot.parse_one(sql, read="tsql")
        column = next(iter(parsed.find_all(ColumnDef)))
        max_length = get_max_length(column)
        assert max_length == 5

    def test_get_max_length_integer_returns_none(self):
        """Should return None for non-string types."""
        sql = "CREATE TABLE t (id INT)"
        parsed = sqlglot.parse_one(sql, read="postgres")
        column = next(iter(parsed.find_all(ColumnDef)))
        max_length = get_max_length(column)
        assert max_length is None

    def test_get_max_length_varchar_without_length(self):
        """Should return None for VARCHAR without length."""
        sql = "CREATE TABLE t (text VARCHAR)"
        parsed = sqlglot.parse_one(sql, read="postgres")
        column = next(iter(parsed.find_all(ColumnDef)))
        max_length = get_max_length(column)
        assert max_length is None


class TestGetPrecisionScale:
    """Test precision and scale extraction from numeric types."""

    def test_get_precision_scale_decimal_both(self):
        """Should extract both precision and scale from DECIMAL."""
        sql = "CREATE TABLE t (amount DECIMAL(10, 2))"
        parsed = sqlglot.parse_one(sql, read="postgres")
        column = next(iter(parsed.find_all(ColumnDef)))
        precision, scale = get_precision_scale(column)
        assert precision == 10
        assert scale == 2

    def test_get_precision_scale_numeric_both(self):
        """Should extract both precision and scale from NUMERIC."""
        sql = "CREATE TABLE t (amount NUMERIC(8, 4))"
        parsed = sqlglot.parse_one(sql, read="postgres")
        column = next(iter(parsed.find_all(ColumnDef)))
        precision, scale = get_precision_scale(column)
        assert precision == 8
        assert scale == 4

    def test_get_precision_scale_precision_only(self):
        """Should extract precision and return scale as 0 when only precision given."""
        sql = "CREATE TABLE t (amount DECIMAL(10))"
        parsed = sqlglot.parse_one(sql, read="postgres")
        column = next(iter(parsed.find_all(ColumnDef)))
        precision, scale = get_precision_scale(column)
        assert precision == 10
        assert scale == 0

    def test_get_precision_scale_number_oracle(self):
        """Should extract precision and scale from NUMBER (Oracle)."""
        sql = "CREATE TABLE t (amount NUMBER(15, 3))"
        parsed = sqlglot.parse_one(sql, read="oracle")
        column = next(iter(parsed.find_all(ColumnDef)))
        precision, scale = get_precision_scale(column)
        assert precision == 15
        assert scale == 3

    def test_get_precision_scale_float(self):
        """Should extract precision from FLOAT."""
        sql = "CREATE TABLE t (value FLOAT(10))"
        parsed = sqlglot.parse_one(sql, read="mysql")
        column = next(iter(parsed.find_all(ColumnDef)))
        precision, _scale = get_precision_scale(column)
        assert precision == 10

    def test_get_precision_scale_integer_returns_none(self):
        """Should return None for non-numeric types."""
        sql = "CREATE TABLE t (id INT)"
        parsed = sqlglot.parse_one(sql, read="postgres")
        column = next(iter(parsed.find_all(ColumnDef)))
        precision, scale = get_precision_scale(column)
        assert precision is None
        assert scale is None

    def test_get_precision_scale_no_params(self):
        """Should return None when no parameters given."""
        sql = "CREATE TABLE t (amount DECIMAL)"
        parsed = sqlglot.parse_one(sql, read="postgres")
        column = next(iter(parsed.find_all(ColumnDef)))
        precision, scale = get_precision_scale(column)
        assert precision is None
        assert scale is None


class TestMapTypeFromSql:
    """Test SQL type to ODCS logical type mapping."""

    def test_map_type_string_types(self):
        """Should map VARCHAR, CHAR, TEXT to string."""
        assert map_type_from_sql("VARCHAR(100)") == "string"
        assert map_type_from_sql("CHAR(10)") == "string"
        assert map_type_from_sql("TEXT") == "string"
        assert map_type_from_sql("NVARCHAR(50)") == "string"
        assert map_type_from_sql("NCHAR(5)") == "string"
        assert map_type_from_sql("NTEXT") == "string"
        assert map_type_from_sql("CLOB") == "string"
        assert map_type_from_sql("NCLOB") == "string"

    def test_map_type_integer_types(self):
        """Should map various integer types to integer."""
        assert map_type_from_sql("INT") == "integer"
        assert map_type_from_sql("INTEGER") == "integer"
        assert map_type_from_sql("BIGINT") == "integer"
        assert map_type_from_sql("TINYINT") == "integer"
        assert map_type_from_sql("SMALLINT") == "integer"

    def test_map_type_byteint(self):
        """Should map BYTEINT (Teradata) to integer."""
        assert map_type_from_sql("BYTEINT") == "integer"

    def test_map_type_numeric_types(self):
        """Should map numeric types to number."""
        assert map_type_from_sql("DECIMAL(10, 2)") == "number"
        assert map_type_from_sql("NUMERIC(8, 4)") == "number"
        assert map_type_from_sql("FLOAT(10)") == "number"
        assert map_type_from_sql("DOUBLE") == "number"
        assert map_type_from_sql("NUMBER(15, 3)") == "number"

    def test_map_type_boolean(self):
        """Should map boolean types to boolean."""
        assert map_type_from_sql("BOOLEAN") == "boolean"
        assert map_type_from_sql("BOOL") == "boolean"
        assert map_type_from_sql("BIT") == "boolean"

    def test_map_type_date(self):
        """Should map DATE to date."""
        assert map_type_from_sql("DATE") == "date"

    def test_map_type_datetime_types(self):
        """Should map datetime types to date."""
        assert map_type_from_sql("DATETIME") == "date"
        assert map_type_from_sql("DATETIME2") == "date"
        assert map_type_from_sql("SMALLDATETIME") == "date"
        assert map_type_from_sql("DATETIMEOFFSET") == "date"
        assert map_type_from_sql("TIMESTAMP") == "date"

    def test_map_type_timestamp(self):
        """Should map TIMESTAMP variants to date."""
        assert map_type_from_sql("TIMESTAMP") == "date"
        assert map_type_from_sql("TIMESTAMP(6)") == "date"

    def test_map_type_interval_oracle(self):
        """Should map INTERVAL to object for Oracle."""
        assert map_type_from_sql("INTERVAL YEAR TO MONTH", Dialects.ORACLE) == "object"
        assert map_type_from_sql("INTERVAL DAY TO SECOND", Dialects.ORACLE) == "object"

    def test_map_type_interval_non_oracle(self):
        """Should map INTERVAL to string for non-Oracle dialects."""
        assert map_type_from_sql("INTERVAL YEAR TO MONTH", Dialects.POSTGRES) == "string"
        assert map_type_from_sql("INTERVAL DAY TO SECOND", Dialects.MYSQL) == "string"

    def test_map_type_binary_types(self):
        """Should map binary types to array."""
        assert map_type_from_sql("BINARY") == "array"
        assert map_type_from_sql("VARBINARY") == "array"
        assert map_type_from_sql("RAW") == "array"
        assert map_type_from_sql("BYTE") == "array"
        assert map_type_from_sql("VARBYTE") == "array"
        assert map_type_from_sql("BLOB") == "array"
        assert map_type_from_sql("BFILE") == "array"

    def test_map_type_json(self):
        """Should map JSON to object."""
        assert map_type_from_sql("JSON") == "object"

    def test_map_type_xml(self):
        """Should map XML to string."""
        assert map_type_from_sql("XML") == "string"

    def test_map_type_unique_identifier(self):
        """Should map UNIQUEIDENTIFIER to string."""
        assert map_type_from_sql("UNIQUEIDENTIFIER") == "string"

    def test_map_type_time(self):
        """Should map TIME to string."""
        assert map_type_from_sql("TIME") == "string"

    def test_map_type_unknown(self):
        """Should map unknown types to object."""
        assert map_type_from_sql("UNKNOWN_TYPE") == "object"

    def test_map_type_case_insensitive(self):
        """Should handle case-insensitive type names."""
        assert map_type_from_sql("varchar(100)") == "string"
        assert map_type_from_sql("INT") == "integer"
        assert map_type_from_sql("Decimal(10,2)") == "number"

    def test_map_type_whitespace_handling(self):
        """Should handle leading and trailing whitespace."""
        assert map_type_from_sql("  VARCHAR(100)  ") == "string"
        assert map_type_from_sql("\tINT\t") == "integer"


class TestReadFile:
    """Test file reading functionality."""

    def test_read_file_existing_file(self, tmp_path):
        """Should read content from existing file."""
        test_file = tmp_path / "test.sql"
        test_content = "CREATE TABLE test (id INT)"
        test_file.write_text(test_content)

        result = read_file(str(test_file))
        assert result == test_content

    def test_read_file_nonexistent_file(self):
        """Should raise DataContractException for nonexistent file."""
        with pytest.raises(DataContractException) as exc_info:
            read_file("/nonexistent/path/file.sql")

        assert "does not exist" in exc_info.value.reason

    def test_read_file_empty_file(self, tmp_path):
        """Should raise DataContractException for empty file."""
        test_file = tmp_path / "empty.sql"
        test_file.write_text("")

        with pytest.raises(DataContractException) as exc_info:
            read_file(str(test_file))

        assert "is empty" in exc_info.value.reason

    def test_read_file_whitespace_only(self, tmp_path):
        """Should raise DataContractException for whitespace-only file."""
        test_file = tmp_path / "whitespace.sql"
        test_file.write_text("   \n\n  \t  ")

        with pytest.raises(DataContractException) as exc_info:
            read_file(str(test_file))

        assert "is empty" in exc_info.value.reason

    def test_read_file_multiline_content(self, tmp_path):
        """Should read multiline content correctly."""
        test_file = tmp_path / "multiline.sql"
        test_content = """CREATE TABLE users (
    id INT PRIMARY KEY,
    name VARCHAR(100)
)"""
        test_file.write_text(test_content)

        result = read_file(str(test_file))
        assert result == test_content
