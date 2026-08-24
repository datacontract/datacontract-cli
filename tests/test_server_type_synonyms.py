"""ODCS lists two spellings for the same system; the CLI implements one of each.

`postgresql` is in the ODCS `Server.type` enum alongside `postgres`, so a
contract may legitimately use it. It resolves to the type the CLI implements,
rather than falling through to "server type not yet supported".
"""

import pytest
from open_data_contract_standard.model import CustomProperty, Server

from datacontract.data_contract import DataContract
from datacontract.model.run import ResultEnum
from datacontract.model.server import get_server_type, normalize_server_type

CONTRACT = """apiVersion: v3.0.2
kind: DataContract
id: orders
name: Orders
version: 1.0.0
status: active
servers:
  - server: production
    type: {server_type}
    host: localhost
    port: 5432
    database: orders
    schema: public
schema:
  - name: orders
    properties:
      - name: order_id
        logicalType: string
        physicalType: text
"""


@pytest.mark.parametrize(
    "declared, resolved",
    [
        ("postgresql", "postgres"),
        ("postgres", "postgres"),
        # a type with no synonym is returned unchanged
        ("snowflake", "snowflake"),
    ],
)
def test_the_server_type_resolves_to_the_spelling_the_cli_implements(declared, resolved):
    assert get_server_type(Server(server="production", type=declared)) == resolved
    assert normalize_server_type(declared) == resolved


def test_a_synonym_resolves_through_the_custom_server_type_too():
    server = Server(
        server="production",
        type="custom",
        customProperties=[CustomProperty(property="customType", value="postgresql")],
    )

    assert get_server_type(server) == "postgres"


@pytest.mark.parametrize("server_type", ["postgres", "postgresql"])
def test_the_contract_is_valid_for_both_spellings(server_type):
    run = DataContract(data_contract_str=CONTRACT.format(server_type=server_type), inline_references=False).lint()

    assert run.result == ResultEnum.passed


@pytest.mark.parametrize("server_type", ["postgres", "postgresql"])
def test_testing_reaches_the_postgres_connector(server_type):
    """Without credentials the run cannot succeed, but it must fail asking for
    Postgres credentials -- not with "server type not yet supported"."""
    run = DataContract(data_contract_str=CONTRACT.format(server_type=server_type), inline_references=False).test()

    reasons = " ".join(check.reason or "" for check in run.checks)
    assert "not yet supported" not in reasons, reasons
    assert "DATACONTRACT_POSTGRES_USERNAME" in reasons, reasons


@pytest.mark.parametrize("server_type", ["postgres", "postgresql"])
def test_export_sql_uses_the_postgres_dialect_for_both_spellings(server_type):
    result = DataContract(data_contract_str=CONTRACT.format(server_type=server_type), inline_references=False).export(
        "sql", sql_server_type="auto"
    )

    assert "-- SQL Dialect: postgres" in result
