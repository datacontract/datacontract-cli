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


def is_read_only_query(query: str, dialect: Optional[str] = None) -> bool:
    """True when `query` is a single read-only statement.

    Fails closed: a query that does not parse is refused rather than passed
    through, and so is one that holds a second statement -- a trailing
    `; DROP TABLE orders` must never reach the data source.
    """
    try:
        statements = sqlglot.parse(query, dialect=dialect)
    except sqlglot.errors.ParseError:
        return False
    except Exception:
        # An unknown dialect name is about the parser, not the query, so try the
        # default dialect rather than refuse a query for how it was labelled.
        try:
            statements = sqlglot.parse(query)
        except Exception:
            return False

    # A trailing semicolon parses as an extra empty statement.
    statements = [statement for statement in statements if statement is not None]
    return len(statements) == 1 and isinstance(statements[0], _READ_ONLY)
