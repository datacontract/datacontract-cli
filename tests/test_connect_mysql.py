"""Unit tests for how connect_ibis attaches MySQL through DuckDB.

These do not hit MySQL: ``duckdb.connect``, the extension loader, and the ibis
wrapper are patched, and we only assert the ATTACH connection string built for
a given set of env vars.
"""

import os

import duckdb
import ibis
import pytest
from open_data_contract_standard.model import OpenDataContractStandard, Server

from datacontract.engines.ibis.connections.connect import connect_ibis
from datacontract.model.run import Run


@pytest.fixture
def env(monkeypatch):
    """The tests assert the exact connection string, so start from a clean slate."""
    for name in list(os.environ):
        if name.startswith("DATACONTRACT_MYSQL_"):
            monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("DATACONTRACT_MYSQL_USERNAME", "reader")
    monkeypatch.setenv("DATACONTRACT_MYSQL_PASSWORD", "secret")
    return monkeypatch


@pytest.fixture
def captured_statements(monkeypatch):
    statements = []

    class FakeConnection:
        def execute(self, sql):
            statements.append(sql)

    monkeypatch.setattr(duckdb, "connect", lambda: FakeConnection())
    monkeypatch.setattr(
        "datacontract.engines.ibis.connections.duckdb_connection._load_extension", lambda con, ext, name: None
    )
    monkeypatch.setattr(ibis.duckdb, "from_connection", lambda con: con)
    return statements


def _server():
    return Server(server="mysql", type="mysql", host="contract-host", port=3307, database="contract_db")


def _connect():
    data_contract = OpenDataContractStandard(apiVersion="v3.0.2", kind="DataContract", id="test", version="1.0.0")
    return connect_ibis(Run.create_run(), data_contract=data_contract, server=_server())


def _attach_statement(statements):
    return next(sql for sql in statements if sql.startswith("ATTACH"))


def test_server_details_come_from_the_contract_by_default(env, captured_statements):
    _connect()

    attach = _attach_statement(captured_statements)
    assert "host=contract-host" in attach
    assert "port=3307" in attach
    assert "database=contract_db" in attach


def test_env_variables_override_the_contract_server_details(env, captured_statements):
    env.setenv("DATACONTRACT_MYSQL_HOST", "env-host")
    env.setenv("DATACONTRACT_MYSQL_PORT", "3308")
    env.setenv("DATACONTRACT_MYSQL_DATABASE", "env_db")

    _connect()

    attach = _attach_statement(captured_statements)
    assert "host=env-host" in attach
    assert "port=3308" in attach
    assert "database=env_db" in attach
