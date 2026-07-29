"""The native type catalog must be read from the contract's schema only.

`information_schema.columns` (and Oracle's `all_tab_columns`) span every schema in
the database, so filtering on the table name alone can pick up a same-named table
in another schema and report its column types. That failure is silent — the query
returns rows either way — and it makes `physicalType` checks pass or fail against
the wrong table.
"""

import pytest
from open_data_contract_standard.model import Server

from datacontract.engines.ibis.native_type import fetch_native_types


class _RecordingBackend:
    """Backend that records the catalog query and answers from a fixed catalog."""

    def __init__(self, rows):
        self._rows = rows
        self.queries = []

    def raw_sql(self, query):
        self.queries.append(query)
        return _Cursor(self._rows)


class _Cursor:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows

    def close(self):
        pass


@pytest.mark.parametrize("server_type", ["sqlserver", "postgres", "redshift", "snowflake", "databricks"])
def test_information_schema_query_is_scoped_to_the_contract_schema(server_type):
    con = _RecordingBackend([("field_one", "varchar", 10, None, None)])
    server = Server(type=server_type, schema="myschema")

    assert fetch_native_types(con, server, "my_table") == {"field_one": "varchar(10)"}
    assert "upper(table_schema) = upper('myschema')" in con.queries[0]


def test_information_schema_query_is_unfiltered_without_a_schema():
    con = _RecordingBackend([("field_one", "varchar", 10, None, None)])

    fetch_native_types(con, Server(type="sqlserver"), "my_table")
    assert "table_schema" not in con.queries[0]


def test_oracle_query_is_scoped_to_the_contract_owner():
    con = _RecordingBackend([("FIELD_ONE", "VARCHAR2", 10, None, None)])
    server = Server(type="oracle", schema="PSD1_VERBIS")

    assert fetch_native_types(con, server, "BERUF") == {"field_one": "VARCHAR2(10)"}
    assert "upper(owner) = upper('PSD1_VERBIS')" in con.queries[0]


def test_full_type_query_is_scoped_to_the_contract_schema():
    con = _RecordingBackend([("field_one", "varchar(10)")])
    server = Server(type="trino", schema="myschema")

    assert fetch_native_types(con, server, "my_table") == {"field_one": "varchar(10)"}
    assert "upper(table_schema) = upper('myschema')" in con.queries[0]


def test_schema_name_is_escaped():
    con = _RecordingBackend([("field_one", "varchar", 10, None, None)])

    fetch_native_types(con, Server(type="sqlserver", schema="it's"), "my_table")
    assert "upper('it''s')" in con.queries[0]
