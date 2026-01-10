"""SQL utility functions for MCP server."""

import sqlglot
from sqlglot import exp


def validate_read_only(sql: str) -> None:
    """Validate that SQL contains only read-only SELECT statements.

    Args:
        sql: SQL query to validate

    Raises:
        ValueError: If SQL is empty, invalid, or contains non-SELECT statements
    """
    if not sql or not sql.strip():
        raise ValueError("SQL query cannot be empty")

    try:
        statements = sqlglot.parse(sql)
    except sqlglot.errors.ParseError as e:
        raise ValueError(f"Invalid SQL syntax: {e}")

    if not statements or all(stmt is None for stmt in statements):
        raise ValueError("No valid SQL statements found")

    # Statement types that modify data or schema
    FORBIDDEN_TYPES = {
        exp.Insert,
        exp.Update,
        exp.Delete,
        exp.Drop,
        exp.Create,
        exp.Alter,
        exp.TruncateTable,
        exp.Merge,
        exp.Grant,
        exp.Revoke,
        exp.Command,  # Catches CALL, EXECUTE, etc.
    }

    for stmt in statements:
        if stmt is None:
            continue

        # Check if statement is a forbidden type
        for forbidden in FORBIDDEN_TYPES:
            if isinstance(stmt, forbidden):
                raise ValueError(f"Only SELECT queries allowed, got: {type(stmt).__name__}")

        # Must be a SELECT statement
        if not isinstance(stmt, exp.Select):
            raise ValueError(f"Only SELECT queries allowed, got: {type(stmt).__name__}")
