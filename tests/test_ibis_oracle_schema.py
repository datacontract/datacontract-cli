"""Unit tests for Oracle table resolution across schemas (owners).

Oracle logs in as one user but the contract's tables may be owned by a different
schema (``server.schema``). ibis defaults the owner to the login user during
introspection, so an unqualified lookup raises ``TableNotFound``. The engine
must qualify the table with the configured schema. See issue: cross-schema
Oracle test fails with "Could not read model '<table>': <table>".
"""

from open_data_contract_standard.model import Server

from datacontract.engines.ibis.ibis_check_execute import _resolve_table, _table_database


class _FakeBackend:
    """Minimal stand-in for an ibis backend that records how it is queried."""

    def __init__(self, name, tables):
        self.name = name
        # tables: {database_or_None: {table_name: object}}
        self._tables = tables
        self.table_calls = []

    def table(self, name, database=None):
        self.table_calls.append((name, database))
        try:
            return self._tables[database][name]
        except KeyError:
            raise Exception(name)

    def list_tables(self, database=None):
        return list(self._tables.get(database, {}))


def test_table_database_uses_server_schema_for_oracle():
    server = Server(type="oracle", schema="PSD1_VERBIS")
    con = _FakeBackend("oracle", {})
    assert _table_database(con, server) == "PSD1_VERBIS"


def test_table_database_none_for_oracle_without_schema():
    server = Server(type="oracle")
    con = _FakeBackend("oracle", {})
    assert _table_database(con, server) is None


def test_table_database_none_for_non_oracle_backend():
    # Postgres/snowflake pin the schema at connect time, so no qualifier is added.
    server = Server(type="postgres", schema="public")
    con = _FakeBackend("postgres", {})
    assert _table_database(con, server) is None


def test_table_database_none_without_server():
    con = _FakeBackend("oracle", {})
    assert _table_database(con, None) is None


def test_resolve_table_qualifies_with_schema():
    sentinel = object()
    con = _FakeBackend("oracle", {"PSD1_VERBIS": {"BERUF": sentinel}})

    assert _resolve_table(con, "BERUF", "PSD1_VERBIS") is sentinel
    assert ("BERUF", "PSD1_VERBIS") in con.table_calls


def test_resolve_table_without_schema_does_not_pass_database():
    sentinel = object()
    con = _FakeBackend("oracle", {None: {"BERUF": sentinel}})

    assert _resolve_table(con, "BERUF") is sentinel
    assert con.table_calls == [("BERUF", None)]


def test_resolve_table_case_insensitive_fallback_keeps_schema():
    sentinel = object()
    con = _FakeBackend("oracle", {"PSD1_VERBIS": {"BERUF": sentinel}})

    # Contract uses lowercase; the actual table is uppercase in the schema.
    assert _resolve_table(con, "beruf", "PSD1_VERBIS") is sentinel
    # The successful resolution still targets the qualifying schema.
    assert con.table_calls[-1] == ("BERUF", "PSD1_VERBIS")
