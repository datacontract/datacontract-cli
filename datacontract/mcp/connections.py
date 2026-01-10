"""Database connection utilities for MCP server using SQLAlchemy."""

import csv
import io
import json
import os
from typing import Any
from urllib.parse import quote_plus

from open_data_contract_standard.model import Server
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

# Supported server types for SQL execution
SUPPORTED_TYPES = {"snowflake", "databricks", "postgres", "bigquery"}


def build_connection_url(server: Server) -> str:
    """Build SQLAlchemy connection URL for the given server.

    Args:
        server: Server configuration from data contract

    Returns:
        SQLAlchemy connection URL string

    Raises:
        ValueError: If server type is unsupported or required credentials are missing
    """
    if server.type == "postgres":
        return _build_postgres_url(server)
    elif server.type == "snowflake":
        return _build_snowflake_url(server)
    elif server.type == "databricks":
        return _build_databricks_url(server)
    elif server.type == "bigquery":
        return _build_bigquery_url(server)
    else:
        raise ValueError(f"Unsupported server type: {server.type}. Supported: {SUPPORTED_TYPES}")


def _build_postgres_url(server: Server) -> str:
    """Build PostgreSQL connection URL."""
    username = os.getenv("DATACONTRACT_POSTGRES_USERNAME")
    password = os.getenv("DATACONTRACT_POSTGRES_PASSWORD")

    if not username:
        raise ValueError("Missing environment variable: DATACONTRACT_POSTGRES_USERNAME")

    password_encoded = quote_plus(password) if password else ""
    port = server.port or 5432

    url = f"postgresql+psycopg2://{username}:{password_encoded}@{server.host}:{port}/{server.database}"

    if server.schema_:
        url += f"?options=-csearch_path%3D{server.schema_}"

    return url


def _build_snowflake_url(server: Server) -> str:
    """Build Snowflake connection URL."""
    username = os.getenv("DATACONTRACT_SNOWFLAKE_USERNAME")
    password = os.getenv("DATACONTRACT_SNOWFLAKE_PASSWORD")
    warehouse = os.getenv("DATACONTRACT_SNOWFLAKE_WAREHOUSE")

    if not username:
        raise ValueError("Missing environment variable: DATACONTRACT_SNOWFLAKE_USERNAME")
    if not password:
        raise ValueError("Missing environment variable: DATACONTRACT_SNOWFLAKE_PASSWORD")

    password_encoded = quote_plus(password)

    url = f"snowflake://{username}:{password_encoded}@{server.account}/{server.database}"

    if server.schema_:
        url += f"/{server.schema_}"

    params = []
    if warehouse:
        params.append(f"warehouse={warehouse}")

    if params:
        url += "?" + "&".join(params)

    return url


def _build_databricks_url(server: Server) -> str:
    """Build Databricks connection URL."""
    token = os.getenv("DATACONTRACT_DATABRICKS_TOKEN")
    http_path = os.getenv("DATACONTRACT_DATABRICKS_HTTP_PATH")

    if not token:
        raise ValueError("Missing environment variable: DATACONTRACT_DATABRICKS_TOKEN")
    if not http_path:
        raise ValueError("Missing environment variable: DATACONTRACT_DATABRICKS_HTTP_PATH")

    host = server.host or os.getenv("DATACONTRACT_DATABRICKS_SERVER_HOSTNAME")
    if not host:
        raise ValueError("Server host not configured and DATACONTRACT_DATABRICKS_SERVER_HOSTNAME not set")

    # Remove https:// prefix if present
    host = host.replace("https://", "").replace("http://", "")

    token_encoded = quote_plus(token)
    http_path_encoded = quote_plus(http_path)

    url = f"databricks://token:{token_encoded}@{host}?http_path={http_path_encoded}"

    if server.catalog:
        url += f"&catalog={server.catalog}"
    if server.schema_:
        url += f"&schema={server.schema_}"

    return url


def _build_bigquery_url(server: Server) -> str:
    """Build BigQuery connection URL."""
    # BigQuery uses Application Default Credentials or service account file
    credentials_path = os.getenv("DATACONTRACT_BIGQUERY_ACCOUNT_INFO_JSON_PATH") or os.getenv(
        "GOOGLE_APPLICATION_CREDENTIALS"
    )

    url = f"bigquery://{server.project}"

    if server.dataset:
        url += f"/{server.dataset}"

    if credentials_path:
        url += f"?credentials_path={quote_plus(credentials_path)}"

    return url


def create_engine_for_server(server: Server) -> Engine:
    """Create SQLAlchemy engine for the given server.

    Args:
        server: Server configuration from data contract

    Returns:
        SQLAlchemy Engine instance
    """
    url = build_connection_url(server)
    return create_engine(url)


def execute_query(engine: Engine, sql: str) -> tuple[list[str], list[dict[str, Any]]]:
    """Execute SQL query and return results.

    Args:
        engine: SQLAlchemy engine
        sql: SQL query to execute

    Returns:
        Tuple of (column_names, rows_as_dicts)
    """
    with engine.connect() as conn:
        result = conn.execute(text(sql))
        columns = list(result.keys())
        rows = [dict(row._mapping) for row in result]
    return columns, rows


def format_results_markdown(columns: list[str], rows: list[dict], server_name: str, server_type: str) -> str:
    """Format query results as a markdown table.

    Args:
        columns: Column names
        rows: List of row dicts
        server_name: Name of the server
        server_type: Type of the server (postgres, snowflake, etc.)

    Returns:
        Markdown formatted string
    """
    if not columns:
        return f"(0 rows from server '{server_name}' [{server_type}])"

    # Build header
    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join(["---"] * len(columns)) + " |"

    # Build rows
    row_lines = []
    for row in rows:
        values = [str(row.get(col, "")) for col in columns]
        row_lines.append("| " + " | ".join(values) + " |")

    lines = [header, separator] + row_lines
    lines.append("")
    lines.append(f"({len(rows)} rows from server '{server_name}' [{server_type}])")

    return "\n".join(lines)


def format_results_json(columns: list[str], rows: list[dict], server_name: str, server_type: str) -> str:
    """Format query results as JSON.

    Args:
        columns: Column names
        rows: List of row dicts
        server_name: Name of the server
        server_type: Type of the server (postgres, snowflake, etc.)

    Returns:
        JSON formatted string
    """
    result = {
        "columns": columns,
        "rows": rows,
        "row_count": len(rows),
        "server": server_name,
        "server_type": server_type,
    }
    return json.dumps(result, default=str)


def format_results_csv(columns: list[str], rows: list[dict]) -> str:
    """Format query results as CSV.

    Args:
        columns: Column names
        rows: List of row dicts

    Returns:
        CSV formatted string
    """
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=columns)
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()
