"""Unit tests for Databricks auth-method selection in connect_ibis.

These do not hit Databricks: ``ibis.databricks.connect`` is patched and we only
assert which auth kwargs the dispatch passes for a given set of env vars.
"""

import ibis
import pytest
from open_data_contract_standard.model import Server

from datacontract.engines.ibis.connections.connect import connect_ibis
from datacontract.model.run import Run

DATABRICKS_ENV_VARS = [
    "DATACONTRACT_DATABRICKS_TOKEN",
    "DATACONTRACT_DATABRICKS_HTTP_PATH",
    "DATACONTRACT_DATABRICKS_SERVER_HOSTNAME",
    "DATACONTRACT_DATABRICKS_CLIENT_ID",
    "DATACONTRACT_DATABRICKS_CLIENT_SECRET",
    "DATACONTRACT_DATABRICKS_PROFILE",
    "DATACONTRACT_DATABRICKS_AUTH_TYPE",
]


@pytest.fixture
def clean_databricks_env(monkeypatch):
    for name in DATABRICKS_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    return monkeypatch


@pytest.fixture
def captured_connect(monkeypatch):
    """Patch ibis.databricks.connect to record the kwargs it is called with."""
    calls = {}

    def fake_connect(**kwargs):
        calls.update(kwargs)
        return "connection"

    monkeypatch.setattr(ibis.databricks, "connect", fake_connect)
    return calls


@pytest.fixture
def patched_databricks_sdk(monkeypatch):
    """Stand in for the Databricks SDK, whose ``Config`` authenticates on construction."""
    from databricks.sdk import core

    recorded = {"oauth_service_principal_result": "service-principal-header-factory"}

    class FakeConfig:
        def __init__(self, **kwargs):
            recorded["config_kwargs"] = kwargs

        def authenticate(self):
            return "unified-auth-header-factory"

    def fake_oauth_service_principal(config):
        assert isinstance(config, FakeConfig)
        return recorded["oauth_service_principal_result"]

    monkeypatch.setattr(core, "Config", FakeConfig)
    monkeypatch.setattr(core, "oauth_service_principal", fake_oauth_service_principal)
    return recorded


def _server():
    return Server(type="databricks", host="dbc-x.cloud.databricks.com", catalog="cat", schema="sch")


def _connect(server=None):
    return connect_ibis(Run.create_run(), data_contract=None, server=server or _server())


def test_personal_access_token_is_default(clean_databricks_env, captured_connect):
    clean_databricks_env.setenv("DATACONTRACT_DATABRICKS_TOKEN", "dapiTOKEN")
    clean_databricks_env.setenv("DATACONTRACT_DATABRICKS_HTTP_PATH", "/sql/1.0/warehouses/abc")

    result = _connect()

    assert result == "connection"
    assert captured_connect["access_token"] == "dapiTOKEN"
    assert captured_connect["http_path"] == "/sql/1.0/warehouses/abc"
    assert captured_connect["server_hostname"] == "dbc-x.cloud.databricks.com"
    assert captured_connect["catalog"] == "cat"
    assert captured_connect["schema"] == "sch"
    assert "credentials_provider" not in captured_connect


def test_oauth_service_principal_m2m(clean_databricks_env, captured_connect):
    clean_databricks_env.setenv("DATACONTRACT_DATABRICKS_CLIENT_ID", "client-id")
    clean_databricks_env.setenv("DATACONTRACT_DATABRICKS_CLIENT_SECRET", "client-secret")

    _connect()

    assert "access_token" not in captured_connect
    assert callable(captured_connect["credentials_provider"])


def test_oauth_service_principal_uses_the_sdk_service_principal_provider(
    clean_databricks_env, captured_connect, patched_databricks_sdk
):
    """Unified auth may resolve M2M credentials to a token the connector's token federation
    then rejects, so the M2M path asks for the service principal provider by name (#1389)."""
    clean_databricks_env.setenv("DATACONTRACT_DATABRICKS_CLIENT_ID", "client-id")
    clean_databricks_env.setenv("DATACONTRACT_DATABRICKS_CLIENT_SECRET", "client-secret")

    _connect()
    header_factory = captured_connect["credentials_provider"]()

    assert header_factory == "service-principal-header-factory"
    assert patched_databricks_sdk["config_kwargs"] == {
        "host": "https://dbc-x.cloud.databricks.com",
        "client_id": "client-id",
        "client_secret": "client-secret",
    }


def test_oauth_service_principal_falls_back_without_oidc_endpoints(
    clean_databricks_env, captured_connect, patched_databricks_sdk
):
    """No OIDC endpoints means no service principal provider, so unified auth stays in charge."""
    patched_databricks_sdk["oauth_service_principal_result"] = None
    clean_databricks_env.setenv("DATACONTRACT_DATABRICKS_CLIENT_ID", "client-id")
    clean_databricks_env.setenv("DATACONTRACT_DATABRICKS_CLIENT_SECRET", "client-secret")

    _connect()
    header_factory = captured_connect["credentials_provider"]()

    assert header_factory() == "unified-auth-header-factory"


def test_config_profile_uses_unified_auth(clean_databricks_env, captured_connect, patched_databricks_sdk):
    """The profile resolves to any of the SDK's auth methods, so it keeps using unified auth."""
    clean_databricks_env.setenv("DATACONTRACT_DATABRICKS_PROFILE", "my-profile")

    _connect()
    header_factory = captured_connect["credentials_provider"]()

    assert header_factory() == "unified-auth-header-factory"
    assert patched_databricks_sdk["config_kwargs"] == {"profile": "my-profile"}


def test_token_wins_over_service_principal(clean_databricks_env, captured_connect):
    clean_databricks_env.setenv("DATACONTRACT_DATABRICKS_TOKEN", "dapiTOKEN")
    clean_databricks_env.setenv("DATACONTRACT_DATABRICKS_CLIENT_ID", "client-id")
    clean_databricks_env.setenv("DATACONTRACT_DATABRICKS_CLIENT_SECRET", "client-secret")

    _connect()

    assert captured_connect["access_token"] == "dapiTOKEN"
    assert "credentials_provider" not in captured_connect


def test_config_profile(clean_databricks_env, captured_connect):
    clean_databricks_env.setenv("DATACONTRACT_DATABRICKS_PROFILE", "my-profile")

    _connect()

    assert "access_token" not in captured_connect
    assert callable(captured_connect["credentials_provider"])


def test_explicit_auth_type_for_u2m_browser(clean_databricks_env, captured_connect):
    clean_databricks_env.setenv("DATACONTRACT_DATABRICKS_AUTH_TYPE", "databricks-oauth")

    _connect()

    assert captured_connect["auth_type"] == "databricks-oauth"
    assert "access_token" not in captured_connect
    assert "credentials_provider" not in captured_connect


def test_hostname_falls_back_to_env(clean_databricks_env, captured_connect):
    clean_databricks_env.setenv("DATACONTRACT_DATABRICKS_TOKEN", "dapiTOKEN")
    clean_databricks_env.setenv("DATACONTRACT_DATABRICKS_SERVER_HOSTNAME", "from-env.cloud.databricks.com")

    _connect(Server(type="databricks", catalog="cat", schema="sch"))

    assert captured_connect["server_hostname"] == "from-env.cloud.databricks.com"


def test_missing_auth_raises(clean_databricks_env, captured_connect):
    from datacontract.model.exceptions import DataContractException

    with pytest.raises(DataContractException):
        _connect()
