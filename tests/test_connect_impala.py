"""Unit tests for the Impala connection options in connect_ibis.

These do not hit Impala: ``ibis.impala.connect`` is patched and we only assert
which kwargs the dispatch passes for a given set of env vars.
"""

import ibis
import pytest
from open_data_contract_standard.model import Server

from datacontract.engines.ibis.connections.connect import connect_ibis
from datacontract.model.run import Run

IMPALA_ENV_VARS = [
    "DATACONTRACT_IMPALA_USERNAME",
    "DATACONTRACT_IMPALA_PASSWORD",
    "DATACONTRACT_IMPALA_USE_SSL",
    "DATACONTRACT_IMPALA_AUTH_MECHANISM",
    "DATACONTRACT_IMPALA_USE_HTTP_TRANSPORT",
    "DATACONTRACT_IMPALA_HTTP_PATH",
]


@pytest.fixture
def env(monkeypatch):
    for name in IMPALA_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    return monkeypatch


@pytest.fixture
def captured_connect(monkeypatch):
    calls = {}

    def fake_connect(**kwargs):
        calls.update(kwargs)
        return "connection"

    monkeypatch.setattr(ibis.impala, "connect", fake_connect)
    return calls


def _server(**kwargs):
    defaults = dict(type="impala", host="my-impala-host", database="my_database")
    defaults.update(kwargs)
    return Server(**defaults)


def _connect(server=None):
    return connect_ibis(Run.create_run(), data_contract=None, server=server or _server())


def test_ldap_over_https_is_default(env, captured_connect):
    env.setenv("DATACONTRACT_IMPALA_USERNAME", "analytics_user")
    env.setenv("DATACONTRACT_IMPALA_PASSWORD", "secret")

    result = _connect()

    assert result == "connection"
    assert captured_connect["host"] == "my-impala-host"
    assert captured_connect["port"] == 443
    assert captured_connect["user"] == "analytics_user"
    assert captured_connect["password"] == "secret"
    assert captured_connect["database"] == "my_database"
    assert captured_connect["use_ssl"] is True
    assert captured_connect["auth_mechanism"] == "LDAP"
    assert captured_connect["use_http_transport"] is True
    assert captured_connect["http_path"] == "cliservice"


def test_server_port_wins_over_the_default(env, captured_connect):
    _connect(_server(port=28000))

    assert captured_connect["port"] == 28000


def test_binary_transport_defaults_to_the_impala_port(env, captured_connect):
    env.setenv("DATACONTRACT_IMPALA_USE_HTTP_TRANSPORT", "false")

    _connect()

    assert captured_connect["port"] == 21050
    assert captured_connect["use_http_transport"] is False
    assert "http_path" not in captured_connect


def test_options_are_overridable(env, captured_connect):
    env.setenv("DATACONTRACT_IMPALA_USE_SSL", "false")
    env.setenv("DATACONTRACT_IMPALA_AUTH_MECHANISM", "GSSAPI")
    env.setenv("DATACONTRACT_IMPALA_HTTP_PATH", "impala/cliservice")

    _connect()

    assert captured_connect["use_ssl"] is False
    assert captured_connect["auth_mechanism"] == "GSSAPI"
    assert captured_connect["http_path"] == "impala/cliservice"
