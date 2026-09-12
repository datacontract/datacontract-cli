"""Unit tests for how connect_ibis maps Postgres connection parameters.

These do not hit Postgres: ``ibis.postgres.connect`` is patched and we only assert
which kwargs the dispatch passes for a given set of env vars.
"""

import os

import ibis
import pytest
from open_data_contract_standard.model import Server

from datacontract.engines.ibis.connections.connect import connect_ibis
from datacontract.model.run import Run


@pytest.fixture
def env(monkeypatch):
    """The tests assert the exact kwargs, so start from a clean slate."""
    for name in list(os.environ):
        if name.startswith("DATACONTRACT_POSTGRES_"):
            monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("DATACONTRACT_POSTGRES_USERNAME", "reader")
    monkeypatch.setenv("DATACONTRACT_POSTGRES_PASSWORD", "secret")
    return monkeypatch


@pytest.fixture
def captured_connect(monkeypatch):
    calls = {}

    def fake_connect(**kwargs):
        calls.update(kwargs)
        return "connection"

    monkeypatch.setattr(ibis.postgres, "connect", fake_connect)
    return calls


def _server():
    return Server(
        server="postgres",
        type="postgres",
        host="contract-host",
        port=5433,
        database="contract_db",
        schema="contract_schema",
    )


def _connect(server=None):
    return connect_ibis(Run.create_run(), data_contract=None, server=server or _server(), config=None)


def test_server_details_come_from_the_contract_by_default(env, captured_connect):
    _connect()

    assert captured_connect == {
        "host": "contract-host",
        "port": 5433,
        "user": "reader",
        "password": "secret",
        "database": "contract_db",
        "schema": "contract_schema",
    }


def test_env_variables_override_the_contract_server_details(env, captured_connect):
    env.setenv("DATACONTRACT_POSTGRES_HOST", "env-host")
    env.setenv("DATACONTRACT_POSTGRES_PORT", "6543")
    env.setenv("DATACONTRACT_POSTGRES_DATABASE", "env_db")
    env.setenv("DATACONTRACT_POSTGRES_SCHEMA", "env_schema")

    _connect()

    assert captured_connect["host"] == "env-host"
    assert captured_connect["port"] == 6543
    assert captured_connect["database"] == "env_db"
    assert captured_connect["schema"] == "env_schema"


def test_port_defaults_to_5432_when_the_contract_has_none(env, captured_connect):
    server = Server(server="postgres", type="postgres", host="contract-host", database="db", schema="public")

    _connect(server)

    assert captured_connect["port"] == 5432
