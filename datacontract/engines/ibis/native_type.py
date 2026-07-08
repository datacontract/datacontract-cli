"""Read the real, declared native column types from a platform's catalog.

The ibis dtype reported by ``table.schema()`` has already collapsed native types
into ibis's own type system (SQL Server ``uniqueidentifier`` becomes ibis
``UUID``, ``nvarchar(255)`` becomes ``String``), so it cannot answer "does the
column exactly match the declared ``physicalType``". This module queries the
platform's own catalog to recover the true declared type, including length and
precision.

``_CATALOG_STRATEGY`` (below) is the single source of truth for which server
types are supported and which catalog-reading strategy each uses. Two catalog
shapes exist:

- engines that expose the type as separate parts (``data_type`` plus length /
  precision / scale), reconstructed by ``reconstruct_native_type``; and
- engines whose ``data_type`` is already a complete type string (Athena,
  BigQuery), used verbatim.

Everything here is best-effort: any failure (unsupported backend, missing
catalog, permission error) returns ``None`` so the caller skips the physical
type check with a warning rather than failing the run.
"""

from __future__ import annotations

import logging
from typing import Optional

from open_data_contract_standard.model import Server

from datacontract.model.server import get_server_type

logger = logging.getLogger(__name__)

# Which server types support native physical type checks, and which catalog
# strategy each uses. Server types not listed here (file sources, the DuckDB
# MySQL scanner, impala, kafka/dataframe) have no usable native declared type,
# so physicalType falls back to the logicalType check. The strategies are
# implemented by the ``_read_*`` readers further down and wired in ``_READERS``.
_CATALOG_STRATEGY = {
    "sqlserver": "information_schema",
    "postgres": "information_schema",
    "redshift": "information_schema",
    "snowflake": "information_schema",
    "databricks": "information_schema",
    "trino": "information_schema",
    "oracle": "oracle",
    "athena": "athena",
    "bigquery": "bigquery",
}


def supports_native_type_introspection(server_type: Optional[str]) -> bool:
    """True when this backend exposes a real declared native type to check against."""
    return server_type in _CATALOG_STRATEGY


# Numeric types whose precision/scale form part of the declared type. Integer
# types also report a numeric_precision, but ``int(10)`` is not a real declared
# type, so precision is only appended for these.
_DECIMAL_TYPES = {"decimal", "numeric", "number", "dec"}

# Oracle reports DATA_LENGTH (in bytes) for every column, but the length is only
# part of the declared type for character and raw types. Appending it elsewhere
# would corrupt types such as ROWID or DATE (``rowid(10)``).
_ORACLE_LENGTH_TYPES = {"char", "nchar", "varchar", "varchar2", "nvarchar2", "raw"}


def reconstruct_native_type(
    data_type: Optional[str],
    char_len=None,
    num_precision=None,
    num_scale=None,
) -> Optional[str]:
    """Rebuild a parameterized native type string from catalog columns.

    ``varchar`` + char_len 255 -> ``varchar(255)`` (``-1`` means SQL Server MAX
    -> ``varchar(max)``); ``decimal`` + precision 10 + scale 2 ->
    ``decimal(10,2)``. Precision is only attached to genuine decimal types.
    """
    if not data_type:
        return None
    base = data_type.strip()
    if not base:
        return None

    if char_len is not None:
        try:
            length = int(char_len)
        except (TypeError, ValueError):
            return base
        return f"{base}(max)" if length < 0 else f"{base}({length})"

    if base.lower() in _DECIMAL_TYPES and num_precision is not None:
        if num_scale:
            return f"{base}({int(num_precision)},{int(num_scale)})"
        return f"{base}({int(num_precision)})"

    return base


def sqlglot_dialect(con):
    """Return the sqlglot dialect for an ibis connection, or ``None``."""
    try:
        return con.compiler.dialect
    except Exception:
        return None


# ---------------------------------------------------------------------------
# low-level catalog query helpers
# ---------------------------------------------------------------------------
def _quote(value: str) -> str:
    return value.replace("'", "''")


def _rows(con, query: str):
    """Execute a raw catalog query and return a list of row tuples, or ``None``."""
    try:
        cursor = con.raw_sql(query)
    except Exception as e:
        logger.debug("native type catalog query failed: %s", e)
        return None
    try:
        if hasattr(cursor, "fetchall"):
            return list(cursor.fetchall())
        # Some backends (e.g. BigQuery) return an iterable result set
        # (RowIterator) instead of a DBAPI cursor.
        return list(cursor)
    except Exception as e:
        logger.debug("could not read native type catalog rows: %s", e)
        return None
    finally:
        # On DuckDB, raw_sql returns the shared connection itself; closing it
        # would tear down the connection and break subsequent checks.
        if cursor is not getattr(con, "con", None):
            try:
                cursor.close()
            except Exception:
                pass


def _map_reconstructed(con, query: str, oracle_length: bool = False) -> Optional[dict[str, str]]:
    """Read ``(column_name, data_type, length, precision, scale)`` rows and
    reconstruct each parameterized native type string."""
    rows = _rows(con, query)
    if not rows:
        return None
    result: dict[str, str] = {}
    for row in rows:
        column_name, data_type = row[0], row[1]
        char_len = row[2]
        if oracle_length:
            # Oracle reports DATA_LENGTH for every column; keep it only for the
            # types where it is really part of the declared type.
            char_len = char_len if (data_type or "").strip().lower() in _ORACLE_LENGTH_TYPES else None
        native = reconstruct_native_type(data_type, char_len, row[3], row[4])
        if column_name and native:
            result[str(column_name).lower()] = native
    return result or None


def _map_full_type(con, query: str) -> Optional[dict[str, str]]:
    """Read ``(column_name, data_type)`` rows where ``data_type`` is already a
    complete native type string."""
    rows = _rows(con, query)
    if not rows:
        return None
    result: dict[str, str] = {}
    for row in rows:
        column_name, data_type = row[0], row[1]
        if column_name and data_type:
            result[str(column_name).lower()] = str(data_type).strip()
    return result or None


# ---------------------------------------------------------------------------
# per-backend catalog readers (one per strategy in _CATALOG_STRATEGY)
# ---------------------------------------------------------------------------
def _read_information_schema(con, server: Server, model: str) -> Optional[dict[str, str]]:
    """Standard ``INFORMATION_SCHEMA.COLUMNS`` with separate length/precision."""
    query = (
        "SELECT column_name, data_type, character_maximum_length, "
        "numeric_precision, numeric_scale "
        f"FROM information_schema.columns WHERE upper(table_name) = upper('{_quote(model)}')"
    )
    return _map_reconstructed(con, query)


def _read_oracle(con, server: Server, model: str) -> Optional[dict[str, str]]:
    """Oracle exposes columns via ``ALL_TAB_COLUMNS`` instead of information_schema."""
    query = (
        "SELECT column_name, data_type, data_length, data_precision, data_scale "
        f"FROM all_tab_columns WHERE upper(table_name) = upper('{_quote(model)}')"
    )
    return _map_reconstructed(con, query, oracle_length=True)


def _read_athena(con, server: Server, model: str) -> Optional[dict[str, str]]:
    """Athena's information_schema.data_type is already a full type string."""
    schema_filter = f" AND table_schema = '{_quote(server.schema_)}'" if server.schema_ else ""
    query = (
        "SELECT column_name, data_type FROM information_schema.columns "
        f"WHERE lower(table_name) = lower('{_quote(model)}'){schema_filter}"
    )
    return _map_full_type(con, query)


def _read_bigquery(con, server: Server, model: str) -> Optional[dict[str, str]]:
    """BigQuery's INFORMATION_SCHEMA must be dataset-qualified; table names are
    case-sensitive and data_type is already a full type string."""
    if not server.project or not server.dataset:
        return None
    query = (
        "SELECT column_name, data_type "
        f"FROM `{server.project}.{server.dataset}`.INFORMATION_SCHEMA.COLUMNS "
        f"WHERE table_name = '{_quote(model)}'"
    )
    return _map_full_type(con, query)


_READERS = {
    "information_schema": _read_information_schema,
    "oracle": _read_oracle,
    "athena": _read_athena,
    "bigquery": _read_bigquery,
}


def fetch_native_types(con, server: Server, model: str) -> Optional[dict[str, str]]:
    """Return ``{column_name_lower: native_type_string}`` for ``model``.

    Returns ``None`` when the native declared type is unavailable for this
    backend, so the caller skips physical type checks rather than failing them.
    """
    strategy = _CATALOG_STRATEGY.get(get_server_type(server))
    return _READERS[strategy](con, server, model) if strategy else None
