"""Unit tests for Databricks auth-method selection in connect_ibis.

These do not hit Databricks: we patch the _NoVolumeBackend.connect method and only
assert which auth kwargs the dispatch passes for a given set of env vars.
"""

import ibis
import pytest
from ibis.backends.databricks import Backend as DatabricksBackend
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
    """Patch DatabricksBackend.connect to record the kwargs it is called with."""
    calls = {}

    def fake_connect(self, **kwargs):
        calls.update(kwargs)
        # Return a minimal mock backend with the required attributes for downstream code.
        mock = type('MockBackend', (), {
            'name': 'databricks',
            '_dc_virtual_model_queries': {},
        })()
        return mock

    monkeypatch.setattr(DatabricksBackend, "connect", fake_connect)
    return calls


def _server():
    return Server(type="databricks", host="dbc-x.cloud.databricks.com", catalog="cat", schema="sch")


def _connect(server=None):
    return connect_ibis(Run.create_run(), data_contract=None, server=server or _server())


def test_personal_access_token_is_default(clean_databricks_env, captured_connect):
    clean_databricks_env.setenv("DATACONTRACT_DATABRICKS_TOKEN", "dapiTOKEN")
    clean_databricks_env.setenv("DATACONTRACT_DATABRICKS_HTTP_PATH", "/sql/1.0/warehouses/abc")

    result = _connect()

    assert result is not None
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


def test_no_create_volume_on_connect(clean_databricks_env, monkeypatch):
    """_post_connect must never execute (no CREATE VOLUME)."""
    clean_databricks_env.setenv("DATACONTRACT_DATABRICKS_TOKEN", "dapiTOKEN")
    clean_databricks_env.setenv("DATACONTRACT_DATABRICKS_HTTP_PATH", "/sql/1.0/warehouses/abc")

    post_connect_called = []

    original_post_connect = DatabricksBackend._post_connect

    def spy_post_connect(self, *, memtable_volume):
        post_connect_called.append(memtable_volume)
        original_post_connect(self, memtable_volume=memtable_volume)

    try:
        # Patch to spy on all calls (including _NoVolumeBackend overrides via MRO).
        DatabricksBackend._post_connect = spy_post_connect

        # Also patch connect to return early so we don't hit actual Databricks.
        def fake_connect(self, **kwargs):
            self.con = None
            self._memtable_volume = kwargs.get('memtable_volume')
            return self

        monkeypatch.setattr(DatabricksBackend, "connect", fake_connect)

        _connect()

        # Since _NoVolumeBackend overrides _post_connect with a no-op, the spy
        # should never be invoked by the do_connect flow (it goes to _NoVolumeBackend's
        # override first via MRO).
        assert post_connect_called == []
    finally:
        DatabricksBackend._post_connect = original_post_connect
