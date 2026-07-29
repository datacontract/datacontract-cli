"""Unit tests for SQL Server table resolution across schemas.

The mssql ibis backend has no ``schema`` kwarg on ``do_connect()``, so tables
living outside the login's default schema (e.g. not ``dbo``) raise
``TableNotFound`` on an unqualified lookup — the same limitation Oracle has.
The engine must qualify the table with the configured schema. See issue:
cross-schema SQL Server test fails with "Could not read model '<table>': <table>".
"""

import pytest
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


# A contract names SQL Server either `sqlserver` (the ODCS spelling) or `mssql`
# (what ODBC, ibis and dbt call it); both must resolve the table the same way.
@pytest.mark.parametrize("server_type", ["sqlserver", "mssql"])
def test_table_database_uses_server_schema_for_sqlserver(server_type):
    server = Server(type=server_type, schema="myschema")
    con = _FakeBackend("mssql", {})
    assert _table_database(con, server) == "myschema"


@pytest.mark.parametrize("server_type", ["sqlserver", "mssql"])
def test_table_database_none_for_sqlserver_without_schema(server_type):
    server = Server(type=server_type)
    con = _FakeBackend("mssql", {})
    assert _table_database(con, server) is None


def test_resolve_table_reads_the_contracted_schema_not_the_login_default():
    # The same table name exists in the contract's schema and in the login's
    # default one; qualifying picks the contract's, rather than silently
    # checking the wrong table's data.
    contracted, decoy = object(), object()
    con = _FakeBackend("mssql", {"myschema": {"my_table": contracted}, None: {"my_table": decoy}})

    server = Server(type="sqlserver", schema="myschema")
    assert _resolve_table(con, "my_table", _table_database(con, server)) is contracted
    assert con.table_calls == [("my_table", "myschema")]
