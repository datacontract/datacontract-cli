"""ODCS v3.2.0 server changes: new types, synonyms, `encoding`, Athena `workgroup`."""

import logging
from unittest.mock import patch

import pytest
from open_data_contract_standard.model import OpenDataContractStandard, Server

from datacontract.data_contract import DataContract
from datacontract.engines.ibis.connections.connect import connect_ibis
from datacontract.export.exporter import _determine_sql_server_type
from datacontract.model.run import ResultEnum, Run
from datacontract.model.server import LINT_ONLY_SERVER_TYPES, get_server_type

CONTRACT = """apiVersion: v3.2.0
kind: DataContract
id: orders
name: Orders
version: 1.0.0
status: active
servers:
  - server: production
{server}
schema:
  - name: orders
    properties:
      - name: order_id
        logicalType: string
        physicalType: VARCHAR
        required: true
      - name: customer
        logicalType: string
        physicalType: VARCHAR
        quality:
          - type: sql
            description: Names keep their umlauts
            query: SELECT count(*) FROM orders WHERE customer = 'Müller'
            mustBe: 1
"""


@pytest.mark.parametrize("declared, resolved", [("fastobjects", "poet"), ("btrieve", "zen"), ("poet", "poet")])
def test_the_actian_synonyms_resolve_to_one_spelling(declared, resolved):
    assert get_server_type(Server(server="s", type=declared)) == resolved


def test_a_lint_only_server_type_explains_itself_instead_of_failing():
    contract = CONTRACT.format(server="    type: exasol\n    host: n11..14.acme.com\n    schema: SALES")

    run = DataContract(data_contract_str=contract).test()

    print(run.pretty())
    assert run.result == ResultEnum.warning
    reason = next(c.reason for c in run.checks if c.name == "Check that server type is supported")
    assert "exasol" in reason and "valid in ODCS" in reason
    assert "exasol" in LINT_ONLY_SERVER_TYPES


def test_an_unknown_dialect_warns_before_falling_back_to_snowflake(caplog):
    contract = OpenDataContractStandard(
        apiVersion="v3.2.0", kind="DataContract", id="x", servers=[Server(server="s", type="teradata")]
    )

    with caplog.at_level(logging.WARNING):
        dialect = _determine_sql_server_type(contract, "auto")

    assert dialect == "snowflake"
    assert "teradata" in caplog.text and "--sql-server-type" in caplog.text


# --- Athena workgroup ------------------------------------------------------------------------


@pytest.fixture
def athena_env(monkeypatch):
    for name in [
        "DATACONTRACT_S3_REGION",
        "DATACONTRACT_S3_ACCESS_KEY_ID",
        "DATACONTRACT_S3_SECRET_ACCESS_KEY",
        "DATACONTRACT_S3_SESSION_TOKEN",
        "DATACONTRACT_ATHENA_CATALOG",
        "DATACONTRACT_ATHENA_SCHEMA",
        "DATACONTRACT_ATHENA_STAGING_DIR",
        "DATACONTRACT_ATHENA_WORKGROUP",
    ]:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("DATACONTRACT_S3_REGION", "eu-central-1")
    return monkeypatch


def _athena(server: Server) -> dict:
    with patch("ibis.athena.connect") as connect:
        connect_ibis(Run.create_run(), None, server)
    return connect.call_args.kwargs


def test_workgroup_is_passed_and_makes_the_staging_dir_optional(athena_env):
    kwargs = _athena(Server(server="athena", type="athena", schema="sales", workgroup="analytics"))

    assert kwargs["work_group"] == "analytics"
    assert "s3_staging_dir" not in kwargs


def test_staging_dir_and_workgroup_are_both_passed(athena_env):
    kwargs = _athena(
        Server(server="athena", type="athena", schema="sales", workgroup="analytics", stagingDir="s3://b/results/")
    )

    assert kwargs["work_group"] == "analytics"
    assert kwargs["s3_staging_dir"] == "s3://b/results/"


def test_the_workgroup_override_wins_over_the_contract(athena_env):
    athena_env.setenv("DATACONTRACT_ATHENA_WORKGROUP", "primary")

    kwargs = _athena(Server(server="athena", type="athena", schema="sales", workgroup="analytics"))

    assert kwargs["work_group"] == "primary"


# --- encoding ---------------------------------------------------------------------------------


def test_csv_files_are_read_in_the_declared_encoding(tmp_path):
    (tmp_path / "orders.csv").write_bytes("order_id,customer\n1,Müller\n".encode("iso-8859-1"))
    contract = CONTRACT.format(
        server=f"    type: local\n    path: {tmp_path}/orders.csv\n    format: csv\n    encoding: ISO-8859-1"
    )

    run = DataContract(data_contract_str=contract).test()

    print(run.pretty())
    assert run.result == ResultEnum.passed


def test_csv_files_default_to_utf8(tmp_path):
    (tmp_path / "orders.csv").write_text("order_id,customer\n1,Müller\n", encoding="utf-8")
    contract = CONTRACT.format(server=f"    type: local\n    path: {tmp_path}/orders.csv\n    format: csv")

    run = DataContract(data_contract_str=contract).test()

    print(run.pretty())
    assert run.result == ResultEnum.passed
