"""Unit tests for Trino auth-method selection in connect_ibis.

These do not hit Trino: ``ibis.trino.connect`` is patched and we only assert
which auth kwargs the dispatch passes for a given set of env vars.
"""

import ibis
import pytest
from open_data_contract_standard.model import Server

from datacontract.engines.ibis.connections.connect import connect_ibis
from datacontract.model.exceptions import DataContractException
from datacontract.model.run import Run

TRINO_ENV_VARS = [
    "DATACONTRACT_TRINO_AUTHENTICATION",
    "DATACONTRACT_TRINO_USERNAME",
    "DATACONTRACT_TRINO_PASSWORD",
    "DATACONTRACT_TRINO_JWT_TOKEN",
]


@pytest.fixture
def env(monkeypatch):
    for name in TRINO_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    return monkeypatch


@pytest.fixture
def captured_connect(monkeypatch):
    calls = {}

    def fake_connect(**kwargs):
        calls.update(kwargs)
        return "connection"

    monkeypatch.setattr(ibis.trino, "connect", fake_connect)
    return calls


def _server(**kwargs):
    defaults = dict(type="trino", host="localhost", port=8080, catalog="memory", schema="default")
    defaults.update(kwargs)
    return Server(**defaults)


def _connect(server=None):
    return connect_ibis(Run.create_run(), data_contract=None, server=server or _server())


def test_basic_auth_is_default(env, captured_connect):
    env.setenv("DATACONTRACT_TRINO_USERNAME", "my_user")
    env.setenv("DATACONTRACT_TRINO_PASSWORD", "secret")

    result = _connect()

    assert result == "connection"
    assert captured_connect["user"] == "my_user"
    assert captured_connect["host"] == "localhost"
    assert captured_connect["port"] == 8080
    assert captured_connect["database"] == "memory"
    assert captured_connect["schema"] == "default"
    assert captured_connect["http_scheme"] == "https"
    assert captured_connect["auth"].__class__.__name__ == "BasicAuthentication"


def test_basic_auth_without_password(env, captured_connect):
    env.setenv("DATACONTRACT_TRINO_USERNAME", "my_user")

    _connect()

    assert captured_connect["user"] == "my_user"
    assert "auth" not in captured_connect
    assert "http_scheme" not in captured_connect


def test_jwt_auth(env, captured_connect):
    env.setenv("DATACONTRACT_TRINO_AUTHENTICATION", "jwt")
    env.setenv("DATACONTRACT_TRINO_JWT_TOKEN", "token-123")

    _connect()

    assert captured_connect["user"] is None
    assert captured_connect["http_scheme"] == "https"
    assert captured_connect["auth"].__class__.__name__ == "JWTAuthentication"
    assert captured_connect["auth"].token == "token-123"


def test_jwt_requires_token(env, captured_connect):
    env.setenv("DATACONTRACT_TRINO_AUTHENTICATION", "jwt")

    with pytest.raises(DataContractException) as exc:
        _connect()

    assert "DATACONTRACT_TRINO_JWT_TOKEN" in exc.value.reason


def test_oauth2_auth(env, captured_connect):
    env.setenv("DATACONTRACT_TRINO_AUTHENTICATION", "oauth2")

    _connect()

    assert captured_connect["user"] is None
    assert captured_connect["http_scheme"] == "https"
    assert captured_connect["auth"].__class__.__name__ == "OAuth2Authentication"


def test_unsupported_authentication_raises(env, captured_connect):
    env.setenv("DATACONTRACT_TRINO_AUTHENTICATION", "kerberos")

    with pytest.raises(DataContractException) as exc:
        _connect()

    assert "DATACONTRACT_TRINO_AUTHENTICATION" in exc.value.reason
    assert "basic, jwt, oauth2" in exc.value.reason


def test_basic_auth_requires_username(env, captured_connect):
    with pytest.raises(DataContractException) as exc:
        _connect()

    assert "DATACONTRACT_TRINO_USERNAME" in exc.value.reason
