"""Regression tests for the Redshift Postgres schema-introspection patch.

Redshift rides ibis's Postgres backend, whose ``get_schema`` query joins
``pg_catalog.pg_enum`` to detect enum columns. Redshift does not expose
``pg_enum``, so the unpatched query fails with ``relation "pg_catalog.pg_enum"
does not exist``. These tests assert the patched query never references
``pg_enum`` and still types columns correctly, without needing a live Redshift.
"""

import contextlib

import pytest

sc = pytest.importorskip("ibis.backends.sql.compilers")

from datacontract.engines.ibis.connections import redshift_patch  # noqa: E402


class _StubCursor:
    def __init__(self, rows):
        self._rows = rows

    def execute(self, sql, params=None, prepare=False):
        self._executed_sql = sql
        return self

    def fetchall(self):
        return self._rows

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _StubPostgresConnection:
    """Minimal stand-in exposing what the patched introspection method touches."""

    name = "postgres"
    compiler = sc.postgres.compiler
    current_database = "dev"
    _session_temp_db = None

    def __init__(self, rows):
        self._cursor = _StubCursor(rows)

    @property
    def con(self):
        return self

    def cursor(self):
        return self._cursor

    @contextlib.contextmanager
    def transaction(self):
        yield


def test_get_schema_query_omits_pg_enum_and_types_columns():
    rows = [
        ("cust_code", "character varying(10)", False),
        ("cust_state", "character varying(24)", True),
    ]
    con = _StubPostgresConnection(rows)

    schema = redshift_patch._get_schema(con, "customer", database="dwh_academic")

    assert "pg_enum" not in con._cursor._executed_sql
    assert schema["cust_code"].is_string()
    assert schema["cust_code"].nullable is False
    assert schema["cust_state"].nullable is True


def test_get_schema_raises_table_not_found_when_empty():
    import ibis.common.exceptions as com

    con = _StubPostgresConnection([])
    with pytest.raises(com.TableNotFound):
        redshift_patch._get_schema(con, "missing", database="dwh_academic")


def test_apply_patch_rebinds_get_schema():
    class _Backend:
        def get_schema(self, *a, **k):  # pragma: no cover - replaced by the patch
            return "original"

    backend = _Backend()
    redshift_patch.apply_redshift_compatibility_patch(backend)

    assert backend.get_schema.__func__ is redshift_patch._get_schema
