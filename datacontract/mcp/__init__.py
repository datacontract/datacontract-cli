"""MCP server module for datacontract-cli."""


def create_mcp_server(name: str = "datacontract"):
    """Create and configure the MCP server.

    Args:
        name: Server name for MCP identification

    Returns:
        Configured FastMCP server instance
    """
    from datacontract.mcp.server import create_mcp_server as _create_mcp_server

    return _create_mcp_server(name)


def run_mcp_server(host: str = "127.0.0.1", port: int = 8000):
    """Run the MCP server.

    Args:
        host: Host to bind to
        port: Port to bind to
    """
    from datacontract.mcp.server import run_mcp_server as _run_mcp_server

    _run_mcp_server(host=host, port=port)


__all__ = ["create_mcp_server", "run_mcp_server"]
