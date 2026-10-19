"""Unit tests for the Hive connection options in connect_ibis.

These do not hit Hive: ``ibis.impala.connect`` is patched and we only assert
which kwargs the dispatch passes, and that the Hive compatibility patch is applied.
"""

import ibis
import pytest
from open_data_contract_standard.model import Server

from datacontract.engines.ibis.connections.connect import connect_ibis
from datacontract.model.run import Run

HIVE_ENV_VARS = [
    "DATACONTRACT_HIVE_USERNAME",
    "DATACONTRACT_HIVE_PASSWORD",
    "DATACONTRACT_HIVE_AUTH_MECHANISM",
    "DATACONTRACT_HIVE_USE_SSL",
    "DATACONTRACT_HIVE_USE_HTTP_TRANSPORT",
    "DATACONTRACT_HIVE_HTTP_PATH",
    "DATACONTRACT_HIVE_HOST",
    "DATACONTRACT_HIVE_PORT",
    "DATACONTRACT_HIVE_DATABASE",
]


class FakeBackend:
    compiler = None


@pytest.fixture
def env(monkeypatch):
    for name in HIVE_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    return monkeypatch


@pytest.fixture
def captured_connect(monkeypatch):
    calls = {}

    def fake_connect(**kwargs):
        calls.update(kwargs)
        return FakeBackend()

    monkeypatch.setattr(ibis.impala, "connect", fake_connect)
    return calls


def _server(**kwargs):
    defaults = dict(type="hive", host="my-hive-host", database="sales")
    defaults.update(kwargs)
    return Server(**defaults)


def _connect(server=None):
    return connect_ibis(Run.create_run(), data_contract=None, server=server or _server())


def test_unconfigured_connection_matches_a_hiveserver2_without_authentication(env, captured_connect):
    """`hive.server2.authentication=NONE` still expects a SASL PLAIN handshake, with any user."""
    _connect()

    assert captured_connect == dict(
        host="my-hive-host",
        port=10000,
        user="hive",
        password="hive",
        database="sales",
        use_ssl=False,
        auth_mechanism="PLAIN",
        use_http_transport=False,
        http_path="",
    )


def test_ldap_over_http_transport(env, captured_connect):
    env.setenv("DATACONTRACT_HIVE_USERNAME", "analyst")
    env.setenv("DATACONTRACT_HIVE_PASSWORD", "secret")
    env.setenv("DATACONTRACT_HIVE_AUTH_MECHANISM", "LDAP")
    env.setenv("DATACONTRACT_HIVE_USE_SSL", "true")
    env.setenv("DATACONTRACT_HIVE_USE_HTTP_TRANSPORT", "true")
    env.setenv("DATACONTRACT_HIVE_HTTP_PATH", "cliservice")

    _connect(_server(port=443))

    assert captured_connect["port"] == 443
    assert captured_connect["user"] == "analyst"
    assert captured_connect["password"] == "secret"
    assert captured_connect["auth_mechanism"] == "LDAP"
    assert captured_connect["use_ssl"] is True
    assert captured_connect["use_http_transport"] is True
    assert captured_connect["http_path"] == "cliservice"


def test_env_variables_override_the_contract_server_details(env, captured_connect):
    env.setenv("DATACONTRACT_HIVE_HOST", "env-host")
    env.setenv("DATACONTRACT_HIVE_PORT", "10001")
    env.setenv("DATACONTRACT_HIVE_DATABASE", "env_db")

    _connect()

    assert captured_connect["host"] == "env-host"
    assert captured_connect["port"] == 10001
    assert captured_connect["database"] == "env_db"


def test_the_connection_groups_by_expression_not_position(env, captured_connect):
    """Hive rejects `GROUP BY 1` with `Expression not in GROUP BY key`."""
    con = _connect()

    table = ibis.table({"order_id": "string"}, name="orders")
    duplicates = table.group_by("order_id").aggregate(n=table.count())

    sql = con.compiler.to_sqlglot(duplicates).sql(dialect=con.compiler.dialect)
    assert "GROUP BY `t0`.`order_id`" in sql
    assert "GROUP BY 1" not in sql
