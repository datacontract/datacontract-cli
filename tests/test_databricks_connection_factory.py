"""Raw SQL and SDK connections share configuration without loading Ibis."""

import builtins
import os
from unittest.mock import Mock

import pytest

from datacontract.connections.databricks import DatabricksConnectionSettings


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for key in os.environ:
        if key.startswith(("DATABRICKS_", "DATACONTRACT_DATABRICKS_")):
            monkeypatch.delenv(key)


def test_config_snapshot_and_server_fallback(monkeypatch):
    monkeypatch.setenv("DATACONTRACT_DATABRICKS_SERVER_HOSTNAME", "canonical.invalid")
    monkeypatch.setenv("DATACONTRACT_DATABRICKS_TOKEN", "first")
    monkeypatch.setenv("DATACONTRACT_DATABRICKS_HTTP_PATH", "/warehouse")
    settings = DatabricksConnectionSettings.from_config(host="fallback.invalid", catalog="main", schema="sales")
    monkeypatch.setenv("DATACONTRACT_DATABRICKS_TOKEN", "second")
    assert settings.sql_options() == dict(
        server_hostname="canonical.invalid",
        http_path="/warehouse",
        access_token="first",
        catalog="main",
        schema="sales",
    )
    assert "first" not in repr(settings)


def test_raw_sql_has_no_ibis_dependency_or_setup_statements(monkeypatch):
    import databricks.sql

    connect = Mock(return_value=Mock())
    monkeypatch.setattr(databricks.sql, "connect", connect)
    original_import = builtins.__import__

    def no_ibis(name, *args, **kwargs):
        if name.startswith("ibis"):
            raise AssertionError("Raw connection must not import ibis")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", no_ibis)
    connection = DatabricksConnectionSettings(host="https://host.invalid/", http_path="/w", token="token").connect_sql()
    assert connection is connect.return_value
    assert connection.mock_calls == []
    assert connect.call_args.kwargs["server_hostname"] == "host.invalid"


@pytest.mark.parametrize(
    "auth,extras",
    [
        ("pat", {"token": "token"}),
        ("oauth-m2m", {"client_id": "id", "client_secret": "secret"}),
        ("azure-cli", {}),
        ("databricks-oauth", {}),
    ],
)
def test_sdk_uses_selected_host_and_authentication(monkeypatch, auth, extras):
    import databricks.sdk

    client = Mock()
    monkeypatch.setattr(databricks.sdk, "WorkspaceClient", client)
    settings = DatabricksConnectionSettings(host="https://host.invalid/", auth_type=auth, **extras)
    assert settings.workspace_client() is client.return_value
    assert client.call_args.kwargs["host"] == "https://host.invalid"
    assert client.call_args.kwargs["auth_type"] == ("oauth-u2m" if auth == "databricks-oauth" else auth)
    assert "http_path" not in client.call_args.kwargs


def test_profile_sql_and_sdk_share_destination_and_refresh(monkeypatch):
    import databricks.sdk
    from databricks.sdk import core

    fake_config = Mock()
    fake_config.authenticate.side_effect = [{"Authorization": "first"}, {"Authorization": "refreshed"}]
    config = Mock(return_value=fake_config)
    client = Mock()
    monkeypatch.setattr(core, "Config", config)
    monkeypatch.setattr(databricks.sdk, "WorkspaceClient", client)
    settings = DatabricksConnectionSettings(host="host.invalid", http_path="/w", profile="profile")
    provider = settings.sql_options()["credentials_provider"]
    config.assert_not_called()
    headers = provider()
    assert headers() == {"Authorization": "first"}
    assert headers() == {"Authorization": "refreshed"}
    settings.workspace_client()
    assert config.call_args.kwargs == client.call_args.kwargs == {"host": "https://host.invalid", "profile": "profile"}


def test_pat_precedence_matches_test_engine():
    settings = DatabricksConnectionSettings(
        host="h",
        http_path="/w",
        token="token",
        client_id="id",
        client_secret="secret",
        profile="profile",
        auth_type="azure-cli",
    )
    assert settings.sql_options()["access_token"] == "token"


@pytest.mark.parametrize("extras", [{"client_id": "id"}, {"client_secret": "secret"}])
def test_incomplete_oauth_credentials_fail_before_connecting(extras):
    settings = DatabricksConnectionSettings(host="h", http_path="/w", **extras)
    with pytest.raises(ValueError, match="both client ID and client secret"):
        settings.connect_sql()
    with pytest.raises(ValueError, match="both client ID and client secret"):
        settings.workspace_client()


def test_provider_errors_do_not_expose_credentials(monkeypatch):
    from databricks.sdk import core

    fake = Mock()
    fake.authenticate.side_effect = RuntimeError("token=private-secret")
    monkeypatch.setattr(core, "Config", Mock(return_value=fake))
    settings = DatabricksConnectionSettings(host="h", http_path="/w", auth_type="azure-cli")
    headers = settings.sql_options()["credentials_provider"]()
    with pytest.raises(RuntimeError, match="refresh failed") as error:
        headers()
    assert "private-secret" not in str(error.value)
    assert error.value.__suppress_context__


def test_missing_http_path_fails_before_opening_sql():
    with pytest.raises(ValueError, match="HTTP path"):
        DatabricksConnectionSettings(host="h", token="t").connect_sql()


@pytest.mark.parametrize("host", ["https://host/path", "user@host", "https://"])
def test_invalid_hosts_fail_before_opening_sql(host):
    with pytest.raises(ValueError, match="hostname"):
        DatabricksConnectionSettings(host=host, http_path="/w", token="t").connect_sql()
