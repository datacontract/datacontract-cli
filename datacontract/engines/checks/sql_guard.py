"""Keep a contract's custom SQL to reading.

A `quality.type: sql` rule computes a number from the data, so a read-only query
is all it ever needs. Anything else -- DDL, DML, `COPY` (a file write on duckdb
and `COPY ... TO PROGRAM` on postgres), `ATTACH`, `INSTALL`/`LOAD`, `SET`,
`PRAGMA`, `CALL` -- is refused, for every data source: a data contract is not
always written by the person whose credentials run it.
"""

from typing import Optional

import sqlglot
from sqlglot import exp

# `Subquery` covers a parenthesized select, `SetOperation` a UNION/INTERSECT/EXCEPT.
# A `WITH ... SELECT` parses as a Select carrying the CTEs.
_READ_ONLY = (exp.Select, exp.SetOperation, exp.Subquery)

# The SQL dialect a quality rule is written in, per ODCS server type. Without it a
# dialect-specific query is parsed as generic SQL and refused for syntax its own
# data source accepts -- BigQuery's backticks, Snowflake's SAMPLE, SQL Server's TOP.
#
# The value is the dialect the *rule author* writes in, which follows from the
# server type they declared. It is not always the engine that ends up running the
# query: the file, kafka and api server types are read through duckdb, and mysql is
# attached through duckdb, but a rule on a mysql server is still written as MySQL.
_DIALECT_BY_SERVER_TYPE = {
    # read through duckdb, and written as duckdb
    "local": "duckdb",
    "s3": "duckdb",
    "gcs": "duckdb",
    "azure": "duckdb",
    "kafka": "duckdb",
    "api": "duckdb",
    "duckdb": "duckdb",
    # spark session backends
    "dataframe": "spark",
    # named by a different spelling in sqlglot
    "sqlserver": "tsql",
    "mssql": "tsql",
    "impala": "hive",
    # same name in sqlglot
    "athena": "athena",
    "bigquery": "bigquery",
    "databricks": "databricks",
    "exasol": "exasol",
    "mysql": "mysql",
    "oracle": "oracle",
    "postgres": "postgres",
    "redshift": "redshift",
    "snowflake": "snowflake",
    "trino": "trino",
}


def dialect_for_server_type(server_type: Optional[str]) -> Optional[str]:
    """The SQL dialect a quality rule on this server type is written in.

    ODCS has no per-rule dialect field, so the server the rule runs against is
    what determines it.
    """
    if server_type is None:
        return None
    return _DIALECT_BY_SERVER_TYPE.get(server_type.lower())


def is_read_only_query(query: str, dialect: Optional[str] = None) -> bool:
    """True when `query` is a single read-only statement."""
    return read_only_query_problem(query, dialect) is None


def read_only_query_problem(query: str, dialect: Optional[str] = None) -> Optional[str]:
    """Why `query` is not a single read-only statement, or None when it is one.

    Fails closed: a query that does not parse is refused rather than passed
    through, and so is one that holds a second statement -- a trailing
    `; DROP TABLE orders` must never reach the data source.
    """
    if dialect == "exasol":
        # ibis registers its own Postgres-based `exasol` dialect over sqlglot's, so by
        # name the parser would depend on whether ibis has been imported yet.
        from sqlglot.dialects.exasol import Exasol as dialect
    try:
        statements = sqlglot.parse(query, dialect=dialect)
    except sqlglot.errors.ParseError as e:
        return f"it could not be parsed: {_describe_parse_error(e)}"
    except Exception:
        # An unknown dialect name is about the parser, not the query, so try the
        # default dialect rather than refuse a query for how it was labelled.
        try:
            statements = sqlglot.parse(query)
        except sqlglot.errors.ParseError as e:
            return f"it could not be parsed: {_describe_parse_error(e)}"
        except Exception as e:
            return f"it could not be parsed: {e}"

    # A trailing semicolon parses as an extra empty statement.
    statements = [statement for statement in statements if statement is not None]
    if not statements:
        return "it is empty"
    if len(statements) > 1:
        return f"it holds {len(statements)} statements"
    statement = statements[0]
    if not isinstance(statement, _READ_ONLY):
        name = statement.this if isinstance(statement, exp.Command) else statement.key
        return f"it is not a read-only query ({str(name).upper()})"
    return None


def _describe_parse_error(error: sqlglot.errors.ParseError) -> str:
    # The message of the error itself underlines the token with terminal escape codes.
    if not error.errors:
        return str(error).splitlines()[0]
    details = error.errors[0]
    return (
        f"{details.get('description')} at line {details.get('line')}, "
        f"column {details.get('col')} (near '{details.get('highlight')}')"
    )
