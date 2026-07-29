"""Unit tests for SQL Server table resolution across schemas.

The mssql ibis backend has no ``schema`` kwarg on ``do_connect()``, so tables
living outside the login's default schema (e.g. not ``dbo``) raise
``TableNotFound`` on an unqualified lookup — the same limitation Oracle has.
The engine must qualify the table with the configured schema. See issue:
cross-schema SQL Server test fails with "Could not read model '<table>': <table>".
"""

from open_data_contract_standard.model import Server

from datacontract.engines.ibis.ibis_check_execute import _table_database


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


def test_table_database_uses_server_schema_for_sqlserver():
    server = Server(type="sqlserver", schema="myschema")
    con = _FakeBackend("mssql", {})
    assert _table_database(con, server) == "myschema"


def test_table_database_none_for_sqlserver_without_schema():
    server = Server(type="sqlserver")
    con = _FakeBackend("mssql", {})
    assert _table_database(con, server) is None
