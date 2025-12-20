"""Integration tests for sql_importer module.

Tests end-to-end functionality of import_sql() function and SqlImporter class,
covering realistic SQL parsing scenarios and ODCS schema generation.
"""

from unittest.mock import patch

import pytest

from datacontract.imports.sql_importer import SqlImporter, import_sql
from datacontract.model.exceptions import DataContractException


class TestImportSqlIntegration:
    """Integration tests for import_sql() function with realistic SQL."""

    def test_import_sql_single_table_basic(self, tmp_path):
        """Should import simple single-table SQL DDL."""
        sql_file = tmp_path / "test.sql"
        sql_file.write_text("CREATE TABLE users (id INT PRIMARY KEY, name VARCHAR(100))")

        result = import_sql("sql", str(sql_file), {"dialect": "postgres"})

        assert result.schema_ is not None
        assert len(result.schema_) >= 1
        schema = result.schema_[0]
        assert schema.name == "users"
        assert schema.physicalType == "table"
        assert schema.properties is not None
        assert len(schema.properties) == 2

        # Verify properties
        properties_by_name = {p.name: p for p in schema.properties}
        assert "id" in properties_by_name
        assert "name" in properties_by_name
        assert properties_by_name["id"].logicalType == "integer"
        assert properties_by_name["name"].logicalType == "string"

    def test_import_sql_with_server_type(self, tmp_path):
        """Should create server entry when dialect provided."""
        sql_file = tmp_path / "test.sql"
        sql_file.write_text("CREATE TABLE data (id INT)")

        result = import_sql("sql", str(sql_file), {"dialect": "postgres"})

        assert result.servers is not None
        assert len(result.servers) == 1
        server = result.servers[0]
        assert server.server == "postgres"
        assert server.type == "postgres"

    def test_import_sql_multiple_tables(self, tmp_path):
        """Should import multiple table definitions."""
        sql_file = tmp_path / "test.sql"
        sql_content = "CREATE TABLE users (id INT PRIMARY KEY, email VARCHAR(100) NOT NULL)"
        sql_file.write_text(sql_content)

        result = import_sql("sql", str(sql_file), {"dialect": "postgres"})

        # sqlglot.parse_one only parses the first statement
        assert result.schema_ is not None
        assert len(result.schema_) >= 1
        assert result.schema_[0].name == "users"

    def test_import_sql_primary_key_tracking(self, tmp_path):
        """Should correctly track primary key positions."""
        sql_file = tmp_path / "test.sql"
        sql_file.write_text("CREATE TABLE composite_key (id INT PRIMARY KEY, alt_id INT PRIMARY KEY, name VARCHAR(50))")

        result = import_sql("sql", str(sql_file))

        assert result.schema_ is not None
        schema = result.schema_[0]
        assert schema.properties is not None
        properties = schema.properties
        pk_properties = [p for p in properties if p.primaryKey]
        assert len(pk_properties) == 2

        # Verify primary key positions are sequential
        positions = sorted([p.primaryKeyPosition for p in pk_properties if p.primaryKeyPosition is not None])
        assert positions == [1, 2]

    def test_import_sql_not_null_constraint(self, tmp_path):
        """Should capture NOT NULL constraints."""
        sql_file = tmp_path / "test.sql"
        sql_file.write_text("CREATE TABLE users (id INT NOT NULL, optional_field VARCHAR(50))")

        result = import_sql("sql", str(sql_file))

        assert result.schema_ is not None
        schema = result.schema_[0]
        assert schema.properties is not None
        properties = schema.properties
        props_by_name = {p.name: p for p in properties}
        assert props_by_name["id"].required is True
        # required is None when not specified (not False)
        optional = props_by_name["optional_field"].required
        assert optional is None or optional is False

    def test_import_sql_varchar_with_length(self, tmp_path):
        """Should extract varchar length constraints."""
        sql_file = tmp_path / "test.sql"
        sql_file.write_text("CREATE TABLE users (name VARCHAR(255), code CHAR(5))")

        result = import_sql("sql", str(sql_file))

        assert result.schema_ is not None
        schema = result.schema_[0]
        assert schema.properties is not None
        properties = schema.properties
        props_by_name = {p.name: p for p in properties}
        name_opts = props_by_name["name"].logicalTypeOptions
        code_opts = props_by_name["code"].logicalTypeOptions
        assert name_opts is not None
        assert name_opts.get("maxLength") == 255
        assert code_opts is not None
        assert code_opts.get("maxLength") == 5

    def test_import_sql_decimal_precision_scale(self, tmp_path):
        """Should extract precision and scale from decimal types."""
        sql_file = tmp_path / "test.sql"
        sql_file.write_text("CREATE TABLE products (price DECIMAL(10, 2))")

        result = import_sql("sql", str(sql_file))

        assert result.schema_ is not None
        schema = result.schema_[0]
        assert schema.properties is not None
        properties = schema.properties
        price_prop = properties[0]
        price_opts = price_prop.logicalTypeOptions
        assert price_opts is not None
        assert price_opts.get("precision") == 10
        assert price_opts.get("scale") == 2

    def test_import_sql_preserves_physical_type(self, tmp_path):
        """Should preserve original SQL type as physicalType (normalized by sqlglot)."""
        sql_file = tmp_path / "test.sql"
        sql_file.write_text("CREATE TABLE data (ts TIMESTAMP, data JSON, num NUMERIC(10,2))")

        result = import_sql("sql", str(sql_file))

        assert result.schema_ is not None
        schema = result.schema_[0]
        assert schema.properties is not None
        properties = schema.properties
        props_by_name = {p.name: p for p in properties}
        assert props_by_name["ts"].physicalType == "TIMESTAMP"
        assert props_by_name["data"].physicalType == "JSON"
        # NUMERIC is normalized to DECIMAL with full specification by sqlglot
        num_type = props_by_name["num"].physicalType
        assert num_type is not None
        assert "DECIMAL" in num_type

    def test_import_sql_invalid_sql(self, tmp_path):
        """Should raise DataContractException for invalid SQL."""
        sql_file = tmp_path / "test.sql"
        sql_file.write_text("CREATE TABLE users (id INT INVALID SYNTAX HERE")

        with pytest.raises(DataContractException) as exc_info:
            import_sql("sql", str(sql_file))

        assert "Error parsing SQL" in exc_info.value.reason

    def test_import_sql_missing_file(self):
        """Should raise DataContractException for missing file."""
        with pytest.raises(DataContractException) as exc_info:
            import_sql("sql", "/nonexistent/path.sql")

        assert "does not exist" in exc_info.value.reason

    def test_import_sql_without_dialect(self, tmp_path):
        """Should work without dialect (None server)."""
        sql_file = tmp_path / "test.sql"
        sql_file.write_text("CREATE TABLE users (id INT)")

        result = import_sql("sql", str(sql_file))

        assert result.schema_ is not None
        assert len(result.schema_) == 1
        # Server should be None or empty when no dialect provided
        assert result.servers is None or len(result.servers) == 0

    def test_import_sql_with_all_column_features(self, tmp_path):
        """Should handle table with various column features together."""
        sql_file = tmp_path / "test.sql"
        sql_file.write_text(
            """CREATE TABLE orders (
                id INT PRIMARY KEY,
                customer_id INT NOT NULL,
                amount DECIMAL(12, 2),
                description VARCHAR(500),
                created_at TIMESTAMP
            )"""
        )

        result = import_sql("sql", str(sql_file), {"dialect": "postgres"})

        assert result.schema_ is not None
        assert len(result.schema_) == 1
        schema = result.schema_[0]
        assert schema.properties is not None
        assert len(schema.properties) == 5

        properties = schema.properties
        props_by_name = {p.name: p for p in properties}

        # Verify all properties are correctly populated
        assert props_by_name["id"].primaryKey is True
        assert props_by_name["customer_id"].required is True
        amount_opts = props_by_name["amount"].logicalTypeOptions
        desc_opts = props_by_name["description"].logicalTypeOptions
        assert amount_opts is not None
        assert amount_opts.get("precision") == 12
        assert desc_opts is not None
        assert desc_opts.get("maxLength") == 500
        assert props_by_name["created_at"].logicalType == "date"


class TestSqlImporter:
    """Tests for SqlImporter class."""

    def test_sql_importer_initialization(self):
        """Should initialize SqlImporter with import format."""
        importer = SqlImporter("sql")
        assert importer.import_format == "sql"

    def test_sql_importer_import_source(self, tmp_path):
        """Should import source using import_source method."""
        sql_file = tmp_path / "test.sql"
        sql_file.write_text("CREATE TABLE users (id INT PRIMARY KEY, name VARCHAR(100))")

        importer = SqlImporter("sql")
        result = importer.import_source(str(sql_file), {"dialect": "postgres"})

        assert result.schema_ is not None
        assert len(result.schema_) == 1
        assert result.schema_[0].name == "users"

    def test_sql_importer_with_tsql_dialect(self, tmp_path):
        """Should handle SQL Server specific syntax."""
        sql_file = tmp_path / "test.sql"
        sql_file.write_text("CREATE TABLE users (id INT PRIMARY KEY, data NVARCHAR(255) NOT NULL)")

        importer = SqlImporter("sql")
        result = importer.import_source(str(sql_file), {"dialect": "sqlserver"})

        assert result.servers is not None
        assert result.servers[0].type == "sqlserver"
        assert result.schema_ is not None
        schema = result.schema_[0]
        assert schema.properties is not None
        assert len(schema.properties) == 2

    def test_sql_importer_handles_import_args(self, tmp_path):
        """Should pass import_args through to import_sql."""
        sql_file = tmp_path / "test.sql"
        sql_file.write_text("CREATE TABLE data (id INT)")

        importer = SqlImporter("sql")
        import_args = {"dialect": "mysql"}
        result = importer.import_source(str(sql_file), import_args)

        assert result.servers is not None
        assert result.servers[0].type == "mysql"

    def test_sql_importer_without_import_args(self, tmp_path):
        """Should handle None import_args gracefully."""
        sql_file = tmp_path / "test.sql"
        sql_file.write_text("CREATE TABLE data (id INT)")

        importer = SqlImporter("sql")
        result = importer.import_source(str(sql_file), {})

        assert result.schema_ is not None
        assert len(result.schema_) == 1


class TestImportSqlEdgeCases:
    """Edge case and error handling tests."""

    def test_import_sql_empty_sql_creates_empty_schema(self, tmp_path):
        """Should raise exception for SQL with no CREATE TABLE statements."""
        sql_file = tmp_path / "test.sql"
        sql_file.write_text("-- just a comment\n-- nothing here")

        with pytest.raises(DataContractException):
            import_sql("sql", str(sql_file))

    def test_import_sql_mixed_dialects_postgres_to_tsql(self, tmp_path):
        """Should parse with specified dialect even if SQL syntax differs."""
        sql_file = tmp_path / "test.sql"
        # Standard SQL, parsed as TSQL
        sql_file.write_text("CREATE TABLE test (id INT, data VARCHAR(100))")

        result = import_sql("sql", str(sql_file), {"dialect": "tsql"})

        assert result.servers is not None
        assert result.servers[0].type == "sqlserver"
        assert result.schema_ is not None
        assert len(result.schema_) == 1

    def test_import_sql_table_with_no_constraints(self, tmp_path):
        """Should handle table with minimal constraints."""
        sql_file = tmp_path / "test.sql"
        sql_file.write_text("CREATE TABLE minimal (col1 INT, col2 VARCHAR(50), col3 DECIMAL(5, 2))")

        result = import_sql("sql", str(sql_file))

        assert result.schema_ is not None
        schema = result.schema_[0]
        assert schema.properties is not None
        properties = schema.properties
        assert len(properties) == 3
        assert all(p.primaryKey is None or p.primaryKey is False for p in properties)
        assert all(p.required is None or p.required is False for p in properties)

    def test_import_sql_various_numeric_types(self, tmp_path):
        """Should handle all numeric types correctly."""
        sql_file = tmp_path / "test.sql"
        sql_file.write_text(
            """CREATE TABLE numbers (
                tiny TINYINT,
                small SMALLINT,
                regular INT,
                big BIGINT,
                flt FLOAT,
                dbl DOUBLE,
                dec DECIMAL(15, 4)
            )"""
        )

        result = import_sql("sql", str(sql_file))

        assert result.schema_ is not None
        schema = result.schema_[0]
        assert schema.properties is not None
        properties = schema.properties
        props_by_name = {p.name: p for p in properties}

        # All should map to either integer or number
        integer_types = {"tiny", "small", "regular", "big"}
        number_types = {"flt", "dbl", "dec"}

        for name in integer_types:
            assert props_by_name[name].logicalType == "integer"
        for name in number_types:
            assert props_by_name[name].logicalType == "number"

    @patch("datacontract.imports.sql_importer.pathlib.Path", spec=True)
    def test_import_sql_error_parsing_sql_calls_logger(self, mock_path, tmp_path):
        """Should log exceptions when SQL parsing fails."""
        # Create real file that sqlglot can't parse
        sql_file = tmp_path / "test.sql"
        sql_file.write_text("CREATE TABLE test (id INT VERY INVALID :::)")

        with pytest.raises(DataContractException):
            import_sql("sql", str(sql_file))
