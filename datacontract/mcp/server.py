"""MCP server implementation for data contract SQL execution."""

import logging
import os
from contextlib import asynccontextmanager
from typing import Optional

from mcp.server.fastmcp import FastMCP

from datacontract.export.odcs_export_helper import get_server_by_name
from datacontract.lint.resolve import resolve_data_contract
from datacontract.mcp.connections import (
    SUPPORTED_TYPES,
    create_engine_for_server,
    execute_query,
    format_results_csv,
    format_results_json,
    format_results_markdown,
)
from datacontract.mcp.sql_utils import validate_read_only

logger = logging.getLogger(__name__)


@asynccontextmanager
async def server_lifespan(mcp: FastMCP):
    """Lifespan context manager for the MCP server."""
    logger.info("Starting datacontract MCP server")
    try:
        yield {}
    finally:
        logger.info("Shutting down datacontract MCP server")


def create_mcp_server(
    name: str = "datacontract",
    host: str = "127.0.0.1",
    port: int = 8000,
) -> FastMCP:
    """Create and configure the MCP server.

    Args:
        name: Server name for MCP identification
        host: Host to bind to
        port: Port to bind to

    Returns:
        Configured FastMCP server instance
    """
    mcp = FastMCP(name, host=host, port=port, lifespan=server_lifespan)

    @mcp.tool()
    def execute_sql(
        sql: str,
        data_contract_path: Optional[str] = None,
        data_contract_yaml: Optional[str] = None,
        server: Optional[str] = None,
        output_format: Optional[str] = "markdown",
    ) -> str:
        """Execute a read-only SQL query against a data source defined in a data contract.

        Args:
            sql: SQL query to execute. Must be a SELECT statement (read-only).
            data_contract_path: Path to data contract YAML file.
            data_contract_yaml: Data contract YAML content as string (alternative to path).
            server: Server name from data contract. If not specified, uses first supported server.
            output_format: Output format - "markdown" (default), "json", or "csv".

        Returns:
            Query results in the specified format.

        Note:
            Database credentials must be configured via environment variables:
            - PostgreSQL: DATACONTRACT_POSTGRES_USERNAME, DATACONTRACT_POSTGRES_PASSWORD
            - Snowflake: DATACONTRACT_SNOWFLAKE_USERNAME, DATACONTRACT_SNOWFLAKE_PASSWORD
            - Databricks: DATACONTRACT_DATABRICKS_TOKEN, DATACONTRACT_DATABRICKS_HTTP_PATH
            - BigQuery: DATACONTRACT_BIGQUERY_ACCOUNT_INFO_JSON_PATH or GOOGLE_APPLICATION_CREDENTIALS
        """
        # Validate inputs
        if not data_contract_path and not data_contract_yaml:
            raise ValueError("Either data_contract_path or data_contract_yaml must be provided")

        if not sql or not sql.strip():
            raise ValueError("SQL query cannot be empty")

        # Validate SQL is read-only
        validate_read_only(sql)

        # Resolve data contract
        data_contract = resolve_data_contract(
            data_contract_location=data_contract_path,
            data_contract_str=data_contract_yaml,
        )

        # Find appropriate server
        selected_server = _get_supported_server(data_contract, server)

        # Execute query
        engine = create_engine_for_server(selected_server)
        try:
            columns, rows = execute_query(engine, sql)
        finally:
            engine.dispose()

        # Format output
        server_name = selected_server.server or "default"
        server_type = selected_server.type

        if output_format == "json":
            return format_results_json(columns, rows, server_name, server_type)
        elif output_format == "csv":
            return format_results_csv(columns, rows)
        else:  # markdown (default)
            return format_results_markdown(columns, rows, server_name, server_type)

    return mcp


def _get_supported_server(data_contract, server_name: Optional[str] = None):
    """Get a supported server from the data contract.

    Args:
        data_contract: Parsed data contract
        server_name: Optional specific server name

    Returns:
        Selected Server object

    Raises:
        ValueError: If no servers or no supported server found
    """
    if not data_contract.servers or len(data_contract.servers) == 0:
        raise ValueError("Data contract has no servers defined")

    if server_name:
        # Find specific server by name
        server = get_server_by_name(data_contract, server_name)
        if server is None:
            available = [s.server for s in data_contract.servers]
            raise ValueError(f"Server '{server_name}' not found. Available: {available}")
        if server.type not in SUPPORTED_TYPES:
            raise ValueError(
                f"Server type '{server.type}' not supported for SQL execution. Supported types: {SUPPORTED_TYPES}"
            )
        return server

    # Find first server with supported type
    for srv in data_contract.servers:
        if srv.type in SUPPORTED_TYPES:
            logger.info(f"Using server '{srv.server}' (type: {srv.type})")
            return srv

    # No supported server found
    available_types = {s.type for s in data_contract.servers}
    raise ValueError(f"No supported server type found. Available: {available_types}. Supported: {SUPPORTED_TYPES}")


def run_mcp_server(host: str = "127.0.0.1", port: int = 8000):
    """Run the MCP server.

    Args:
        host: Host to bind to
        port: Port to bind to
    """
    # Check for auth token
    token = os.getenv("DATACONTRACT_MCP_TOKEN")
    if not token:
        logger.warning(
            "WARNING: DATACONTRACT_MCP_TOKEN not set. Running without authentication. "
            "This is not recommended for production deployments."
        )

    mcp = create_mcp_server(host=host, port=port)
    mcp.run(transport="streamable-http")
