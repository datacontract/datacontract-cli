"""Unit tests for MCP database connections."""


import pytest
from open_data_contract_standard.model import Server

from datacontract.mcp.connections import (
    SUPPORTED_TYPES,
    build_connection_url,
    format_results_csv,
    format_results_json,
    format_results_markdown,
)


class TestBuildConnectionUrl:
    """Tests for building SQLAlchemy connection URLs."""

    def test_postgres_url(self, monkeypatch):
        """Test PostgreSQL URL building."""
        monkeypatch.setenv("DATACONTRACT_POSTGRES_USERNAME", "testuser")
        monkeypatch.setenv("DATACONTRACT_POSTGRES_PASSWORD", "testpass")

        server = Server(type="postgres", host="localhost", port=5432, database="testdb", schema_="public")

        url = build_connection_url(server)

        assert url.startswith("postgresql+psycopg2://")
        assert "testuser" in url
        assert "localhost:5432" in url
        assert "testdb" in url

    def test_postgres_missing_credentials(self, monkeypatch):
        """Test PostgreSQL fails without credentials."""
        monkeypatch.delenv("DATACONTRACT_POSTGRES_USERNAME", raising=False)
        monkeypatch.delenv("DATACONTRACT_POSTGRES_PASSWORD", raising=False)

        server = Server(type="postgres", host="localhost", port=5432, database="testdb")

        with pytest.raises(ValueError, match="DATACONTRACT_POSTGRES_USERNAME"):
            build_connection_url(server)

    def test_snowflake_url(self, monkeypatch):
        """Test Snowflake URL building."""
        monkeypatch.setenv("DATACONTRACT_SNOWFLAKE_USERNAME", "testuser")
        monkeypatch.setenv("DATACONTRACT_SNOWFLAKE_PASSWORD", "testpass")

        server = Server(type="snowflake", account="myaccount", database="testdb", schema_="public")

        url = build_connection_url(server)

        assert url.startswith("snowflake://")
        assert "testuser" in url
        assert "myaccount" in url
        assert "testdb" in url

    def test_snowflake_missing_credentials(self, monkeypatch):
        """Test Snowflake fails without credentials."""
        monkeypatch.delenv("DATACONTRACT_SNOWFLAKE_USERNAME", raising=False)
        monkeypatch.delenv("DATACONTRACT_SNOWFLAKE_PASSWORD", raising=False)

        server = Server(type="snowflake", account="myaccount", database="testdb", schema_="public")

        with pytest.raises(ValueError, match="DATACONTRACT_SNOWFLAKE_USERNAME"):
            build_connection_url(server)

    def test_databricks_url(self, monkeypatch):
        """Test Databricks URL building."""
        monkeypatch.setenv("DATACONTRACT_DATABRICKS_TOKEN", "testtoken")
        monkeypatch.setenv("DATACONTRACT_DATABRICKS_HTTP_PATH", "/sql/1.0/endpoints/abc123")

        server = Server(type="databricks", host="myhost.databricks.com", catalog="mycatalog", schema_="myschema")

        url = build_connection_url(server)

        assert url.startswith("databricks://")
        assert "myhost.databricks.com" in url
        assert "testtoken" in url

    def test_databricks_missing_token(self, monkeypatch):
        """Test Databricks fails without token."""
        monkeypatch.delenv("DATACONTRACT_DATABRICKS_TOKEN", raising=False)

        server = Server(type="databricks", host="myhost.databricks.com", catalog="mycatalog", schema_="myschema")

        with pytest.raises(ValueError, match="DATACONTRACT_DATABRICKS_TOKEN"):
            build_connection_url(server)

    def test_bigquery_url(self, monkeypatch):
        """Test BigQuery URL building."""
        server = Server(type="bigquery", project="myproject", dataset="mydataset")

        url = build_connection_url(server)

        assert url.startswith("bigquery://")
        assert "myproject" in url

    def test_unsupported_type(self):
        """Test unsupported server type fails."""
        server = Server(type="mysql", host="localhost", database="testdb")

        with pytest.raises(ValueError, match="Unsupported server type"):
            build_connection_url(server)


class TestSupportedTypes:
    """Tests for supported database types."""

    def test_supported_types_contains_postgres(self):
        assert "postgres" in SUPPORTED_TYPES

    def test_supported_types_contains_snowflake(self):
        assert "snowflake" in SUPPORTED_TYPES

    def test_supported_types_contains_databricks(self):
        assert "databricks" in SUPPORTED_TYPES

    def test_supported_types_contains_bigquery(self):
        assert "bigquery" in SUPPORTED_TYPES


class TestFormatResults:
    """Tests for result formatting functions."""

    def test_format_markdown(self):
        """Test markdown table formatting."""
        columns = ["id", "name", "amount"]
        rows = [
            {"id": 1, "name": "Alice", "amount": 100.50},
            {"id": 2, "name": "Bob", "amount": 200.00},
        ]

        result = format_results_markdown(columns, rows, "production", "postgres")

        assert "| id | name | amount |" in result
        assert "| 1 | Alice | 100.5 |" in result
        assert "| 2 | Bob | 200.0 |" in result
        assert "(2 rows from server 'production' [postgres])" in result

    def test_format_markdown_empty(self):
        """Test markdown with empty results."""
        columns = ["id", "name"]
        rows = []

        result = format_results_markdown(columns, rows, "production", "postgres")

        assert "| id | name |" in result
        assert "(0 rows" in result

    def test_format_json(self):
        """Test JSON formatting."""
        columns = ["id", "name"]
        rows = [{"id": 1, "name": "Alice"}]

        result = format_results_json(columns, rows, "production", "postgres")

        assert '"columns": ["id", "name"]' in result
        assert '"row_count": 1' in result
        assert '"server": "production"' in result

    def test_format_csv(self):
        """Test CSV formatting."""
        columns = ["id", "name", "amount"]
        rows = [
            {"id": 1, "name": "Alice", "amount": 100.50},
            {"id": 2, "name": "Bob", "amount": 200.00},
        ]

        result = format_results_csv(columns, rows)

        # Replace CRLF with LF for cross-platform compatibility
        lines = result.replace("\r\n", "\n").strip().split("\n")
        assert lines[0] == "id,name,amount"
        assert lines[1] == "1,Alice,100.5"
        assert lines[2] == "2,Bob,200.0"

    def test_format_csv_with_comma_in_value(self):
        """Test CSV escaping for values containing commas."""
        columns = ["id", "description"]
        rows = [{"id": 1, "description": "Hello, World"}]

        result = format_results_csv(columns, rows)

        # Value with comma should be quoted
        assert '"Hello, World"' in result
