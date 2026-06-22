"""Regression tests for the Oracle pre-23ai schema-introspection patch.

ibis renders the nullable flag in its column-metadata query as a bare
``NULLABLE = 'Y'`` boolean projection. Oracle only added a SQL boolean type in
23ai, so the unpatched query raises ``ORA-00923: FROM keyword not found where
expected`` on 19c/21c. The CI test container runs 23ai and therefore cannot
catch this, so these tests assert the patched query is boolean-free without
needing a live database.
"""

import contextlib

import pytest

sc = pytest.importorskip("ibis.backends.sql.compilers")

from datacontract.engines.ibis.connections import oracle_patch  # noqa: E402


class _StubCursor:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows


class _StubOracleConnection:
    """Minimal stand-in exposing what the patched introspection methods touch."""

    name = "oracle"
    compiler = sc.oracle.compiler

    def __init__(self, rows):
        self._rows = rows
        self.captured_sql = None

    @contextlib.contextmanager
    def _safe_raw_sql(self, stmt):
        # Render exactly as ibis's raw_sql does before executing.
        self.captured_sql = stmt.sql(dialect=self.name)
        yield _StubCursor(self._rows)


def _assert_pre_23ai_compatible(sql: str):
    assert "CASE WHEN" in sql
    # The unpatched, pre-23ai-incompatible projection must not appear.
    assert "= 'Y' AS" not in sql.upper().replace("NULLABLE = 'Y' THEN", "")


def test_get_schema_query_is_boolean_free_and_typed():
    rows = [
        ("ID", "NUMBER", 10, 0, 1),
        ("NAME", "VARCHAR2", None, None, 0),
    ]
    con = _StubOracleConnection(rows)

    schema = oracle_patch._get_schema(con, "MY_TABLE", database="MY_OWNER")

    _assert_pre_23ai_compatible(con.captured_sql)
    # The 1/0 flag from CASE is coerced back to a Python bool on the field type.
    assert schema["ID"].nullable is True
    assert schema["NAME"].nullable is False
    assert schema["ID"].is_integer()
    assert schema["NAME"].is_string()


def test_get_schema_raises_table_not_found_when_empty():
    import ibis.common.exceptions as exc

    con = _StubOracleConnection([])
    with pytest.raises(exc.TableNotFound):
        oracle_patch._get_schema(con, "MISSING", database="MY_OWNER")


def test_apply_patch_rebinds_methods():
    class _Backend:
        def get_schema(self, *a, **k):  # pragma: no cover - replaced by the patch
            return "original"

        def _get_schema_using_query(self, *a, **k):  # pragma: no cover
            return "original"

    backend = _Backend()
    oracle_patch.apply_oracle_compatibility_patch(backend)

    assert backend.get_schema.__func__ is oracle_patch._get_schema
    assert backend._get_schema_using_query.__func__ is oracle_patch._get_schema_using_query
