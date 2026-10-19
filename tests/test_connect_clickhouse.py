"""Unit tests for the ClickHouse connection options in connect_ibis.

These do not hit ClickHouse: ``ibis.clickhouse.connect`` is patched and we only
assert which kwargs the dispatch passes for a given contract and set of env vars.
"""

import ibis
import pytest
from open_data_contract_standard.model import Server

from datacontract.engines.ibis.connections.connect import connect_ibis
from datacontract.model.run import Run

CLICKHOUSE_ENV_VARS = [
    "DATACONTRACT_CLICKHOUSE_USERNAME",
    "DATACONTRACT_CLICKHOUSE_PASSWORD",
    "DATACONTRACT_CLICKHOUSE_SECURE",
    "DATACONTRACT_CLICKHOUSE_HOST",
    "DATACONTRACT_CLICKHOUSE_PORT",
    "DATACONTRACT_CLICKHOUSE_DATABASE",
]


@pytest.fixture
def env(monkeypatch):
    for name in CLICKHOUSE_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    return monkeypatch


@pytest.fixture
def captured_connect(monkeypatch):
    calls = {}

    def fake_connect(**kwargs):
        calls.update(kwargs)
        return "connection"

    monkeypatch.setattr(ibis.clickhouse, "connect", fake_connect)
    return calls


def _server(**kwargs):
    defaults = dict(type="clickhouse", host="my-clickhouse-host", port=8123, database="sales")
    defaults.update(kwargs)
    return Server(**defaults)


def _connect(server=None, run=None):
    return connect_ibis(run or Run.create_run(), data_contract=None, server=server or _server())


def test_unconfigured_connection_uses_the_clickhouse_defaults(env, captured_connect):
    result = _connect(_server(port=None))

    assert result == "connection"
    assert captured_connect == dict(
        host="my-clickhouse-host",
        port=8123,
        database="sales",
        user="default",
        password="",
        secure=False,
    )


def test_credentials_come_from_the_environment(env, captured_connect):
    env.setenv("DATACONTRACT_CLICKHOUSE_USERNAME", "analyst")
    env.setenv("DATACONTRACT_CLICKHOUSE_PASSWORD", "secret")

    _connect()

    assert captured_connect["user"] == "analyst"
    assert captured_connect["password"] == "secret"


def test_secure_connections_default_to_the_https_port(env, captured_connect):
    env.setenv("DATACONTRACT_CLICKHOUSE_SECURE", "true")

    _connect(_server(port=None))

    assert captured_connect["secure"] is True
    assert captured_connect["port"] == 8443


@pytest.mark.parametrize("native_port, http_port", [(9000, 8123), (9440, 8443)])
def test_the_native_protocol_port_is_replaced_by_the_http_port(env, captured_connect, native_port, http_port):
    """clickhouse-connect speaks HTTP only, while contracts often name the port of clickhouse-client."""
    run = Run.create_run()

    _connect(_server(port=native_port), run)

    assert captured_connect["port"] == http_port
    assert any(f"Port {native_port} is ClickHouse's native protocol port" in log.message for log in run.logs)


def test_any_other_port_is_used_as_given(env, captured_connect):
    _connect(_server(port=18123))

    assert captured_connect["port"] == 18123


def test_env_variables_override_the_contract_server_details(env, captured_connect):
    env.setenv("DATACONTRACT_CLICKHOUSE_HOST", "env-host")
    env.setenv("DATACONTRACT_CLICKHOUSE_PORT", "28123")
    env.setenv("DATACONTRACT_CLICKHOUSE_DATABASE", "env_db")

    _connect()

    assert captured_connect["host"] == "env-host"
    assert captured_connect["port"] == 28123
    assert captured_connect["database"] == "env_db"
