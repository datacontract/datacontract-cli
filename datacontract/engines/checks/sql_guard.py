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


def sqlglot_dialect(dialect: Optional[str]):
    """The sqlglot dialect to read and write `dialect` SQL with."""
    if dialect == "exasol":
        # ibis registers its own Postgres-based `exasol` dialect over sqlglot's, so by
        # name the dialect would depend on whether ibis has been imported yet.
        from sqlglot.dialects.exasol import Exasol

        return Exasol
    return dialect


def refusal_reason(query: str, dialect: Optional[str] = None) -> Optional[str]:
    """Why `query` is refused, or None when it is a single read-only statement.

    Fails closed: a query that does not parse is refused rather than passed
    through, and so is one that holds a second statement -- a trailing
    `; DROP TABLE orders` must never reach the data source.
    """
    read_as = dialect
    try:
        statements = sqlglot.parse(query, dialect=sqlglot_dialect(dialect))
    except sqlglot.errors.SqlglotError as e:
        return _unreadable(e, read_as)
    except Exception:
        # An unknown dialect name is about the parser, not the query, so try the
        # default dialect rather than refuse a query for how it was labelled.
        read_as = None
        try:
            statements = sqlglot.parse(query)
        except sqlglot.errors.SqlglotError as e:
            return _unreadable(e, read_as)
        except Exception:
            statements = []

    # A trailing semicolon parses as an extra empty statement.
    statements = [statement for statement in statements if statement is not None]
    if len(statements) == 1 and isinstance(statements[0], _READ_ONLY):
        return None
    return (
        f"A quality rule query must be a single read-only query, and this one could "
        f"not be read as one{f' ({read_as} SQL)' if read_as else ''}, so it was not executed."
    )


def _unreadable(error: sqlglot.errors.SqlglotError, dialect: Optional[str]) -> str:
    # `str(error)` of a ParseError carries terminal escape codes around the offending token.
    if isinstance(error, sqlglot.errors.ParseError) and error.errors:
        first = error.errors[0]
        description = first["description"]
        # e.g. "Required keyword: 'this' missing for <class 'sqlglot.expressions.Where'>"
        if description.startswith("Required keyword"):
            description = "Incomplete expression"
        detail = f'{description} at line {first["line"]}, column {first["col"]}, near "{first["highlight"]}"'
    else:
        detail = str(error)
    return f"The query could not be read{f' as {dialect} SQL' if dialect else ''}: {detail}, so it was not executed."
