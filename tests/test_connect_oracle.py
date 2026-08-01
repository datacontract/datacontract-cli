"""Unit tests for how connect_ibis maps Oracle connection parameters.

These do not hit Oracle: ``ibis.oracle.connect`` and the compatibility patch are
patched, and we only assert which kwargs the dispatch passes for a given set of
env vars.
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
        if name.startswith("DATACONTRACT_ORACLE_"):
            monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("DATACONTRACT_ORACLE_USERNAME", "reader")
    monkeypatch.setenv("DATACONTRACT_ORACLE_PASSWORD", "secret")
    return monkeypatch


@pytest.fixture
def captured_connect(monkeypatch):
    calls = {}

    def fake_connect(**kwargs):
        calls.update(kwargs)
        return "connection"

    monkeypatch.setattr(ibis.oracle, "connect", fake_connect)
    monkeypatch.setattr(
        "datacontract.engines.ibis.connections.oracle_patch.apply_oracle_compatibility_patch", lambda con: None
    )
    return calls


def _server():
    return Server(server="oracle", type="oracle", host="contract-host", port=1522, serviceName="CONTRACT_SVC")


def _connect(server=None):
    return connect_ibis(Run.create_run(), data_contract=None, server=server or _server())


def test_server_details_come_from_the_contract_by_default(env, captured_connect):
    _connect()

    assert captured_connect == {
        "host": "contract-host",
        "port": 1522,
        "user": "reader",
        "password": "secret",
        "service_name": "CONTRACT_SVC",
    }


def test_env_variables_override_the_contract_server_details(env, captured_connect):
    env.setenv("DATACONTRACT_ORACLE_HOST", "env-host")
    env.setenv("DATACONTRACT_ORACLE_PORT", "1523")
    env.setenv("DATACONTRACT_ORACLE_SERVICE_NAME", "ENV_SVC")

    _connect()

    assert captured_connect["host"] == "env-host"
    assert captured_connect["port"] == 1523
    assert captured_connect["service_name"] == "ENV_SVC"
