"""`mssql` and `sqlserver` name the same platform and are handled identically.

ODCS spells it `sqlserver`; ODBC, ibis and dbt call it `mssql`, so contracts
arrive written either way. Both values are accepted as they are — neither is
rewritten to the other. `mssql` is not in the ODCS `server.type` enum, so an ODCS
contract carries it through the standard's `custom` escape hatch, while a DCS
contract can name it directly.
"""

import pytest
from open_data_contract_standard.model import CustomProperty, SchemaProperty, Server

from datacontract.engines.ibis.ibis_check_execute import _table_database
from datacontract.engines.ibis.native_type import supports_native_type_introspection
from datacontract.export.sql_type_converter import convert_to_sql_type
from datacontract.lint.resolve import resolve_data_contract
from datacontract.model.server import get_server_type

DCS_CONTRACT = """
dataContractSpecification: 1.2.1
id: mssql-spelling
info:
  title: mssql-spelling
  version: 0.0.1
servers:
  prod:
    type: {server_type}
    host: localhost
    port: 1433
    database: mydb
    schema: myschema
models:
  my_table:
    type: table
    fields:
      field_one:
        type: varchar
"""


class _MssqlBackend:
    """Stand-in for a connected ibis mssql backend, whatever the contract spelled."""

    name = "mssql"


@pytest.mark.parametrize("server_type", ["sqlserver", "mssql"])
def test_dcs_contract_keeps_the_spelling_it_was_written_with(server_type):
    contract = resolve_data_contract(data_contract_str=DCS_CONTRACT.format(server_type=server_type))
    assert contract.servers[0].type == server_type


@pytest.mark.parametrize("server_type", ["sqlserver", "mssql"])
def test_native_type_introspection_is_supported(server_type):
    assert supports_native_type_introspection(server_type)


@pytest.mark.parametrize("server_type", ["sqlserver", "mssql"])
def test_table_is_qualified_with_the_contract_schema(server_type):
    assert _table_database(_MssqlBackend(), Server(type=server_type, schema="myschema")) == "myschema"


def test_odcs_custom_type_mssql_is_a_sql_server():
    # ODCS only defines `sqlserver`, so an ODCS contract spells `mssql` through
    # `type: custom` + `customType`.
    server = Server(
        type="custom",
        schema="myschema",
        customProperties=[CustomProperty(property="customType", value="mssql")],
    )
    assert get_server_type(server) == "mssql"
    assert _table_database(_MssqlBackend(), server) == "myschema"


def test_sql_type_conversion_is_identical():
    field = SchemaProperty(name="field_one", logicalType="string", logicalTypeOptions={"maxLength": 10})
    assert convert_to_sql_type(field, "mssql") == convert_to_sql_type(field, "sqlserver")
