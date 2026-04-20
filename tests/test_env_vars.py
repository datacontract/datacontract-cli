import pytest

from datacontract.engines.soda.connections.databricks import to_databricks_soda_configuration
from datacontract.engines.soda.connections.sqlserver import to_sqlserver_soda_configuration
from datacontract.engines.soda.connections.trino import to_trino_soda_configuration
from datacontract.model.exceptions import DataContractException, require_env


class _Server:
    type = "postgres"
    host = "localhost"
    port = 5432
    database = "db"
    schema_ = "public"
    catalog = None
    serviceName = None


def test_require_env_returns_value_when_set(monkeypatch):
    monkeypatch.setenv("DATACONTRACT_TEST_VAR", "hello")

    assert require_env("DATACONTRACT_TEST_VAR", server_type="postgres") == "hello"


def test_require_env_raises_when_unset(monkeypatch):
    monkeypatch.delenv("DATACONTRACT_TEST_VAR", raising=False)

    with pytest.raises(DataContractException) as exc_info:
        require_env("DATACONTRACT_TEST_VAR", server_type="postgres")

    reason = exc_info.value.reason
    assert "DATACONTRACT_TEST_VAR" in reason
    assert "postgres" in reason
    assert exc_info.value.type == "postgres-connection"


def test_require_env_raises_when_empty(monkeypatch):
    monkeypatch.setenv("DATACONTRACT_TEST_VAR", "")

    with pytest.raises(DataContractException):
        require_env("DATACONTRACT_TEST_VAR", server_type="postgres")


def test_require_env_includes_hint(monkeypatch):
    monkeypatch.delenv("DATACONTRACT_TEST_VAR", raising=False)

    with pytest.raises(DataContractException) as exc_info:
        require_env(
            "DATACONTRACT_TEST_VAR",
            server_type="postgres",
            hint="See README for details.",
        )

    assert "See README for details." in exc_info.value.reason


def test_trino_no_auth_when_password_missing(monkeypatch):
    monkeypatch.setenv("DATACONTRACT_TRINO_USERNAME", "user")
    monkeypatch.delenv("DATACONTRACT_TRINO_PASSWORD", raising=False)

    result = to_trino_soda_configuration(_Server())

    assert "auth_type: NoAuthentication" in result


def test_sqlserver_trusted_connection_does_not_require_creds(monkeypatch):
    from open_data_contract_standard.model import Server

    monkeypatch.delenv("DATACONTRACT_SQLSERVER_USERNAME", raising=False)
    monkeypatch.delenv("DATACONTRACT_SQLSERVER_PASSWORD", raising=False)
    monkeypatch.setenv("DATACONTRACT_SQLSERVER_TRUSTED_CONNECTION", "true")
    monkeypatch.delenv("DATACONTRACT_SQLSERVER_AUTHENTICATION", raising=False)

    server = Server(type="sqlserver", host="h", port=1433, database="db", schema="dbo")
    # Should not raise
    to_sqlserver_soda_configuration(server)


def test_databricks_raises_when_host_missing(monkeypatch):
    monkeypatch.setenv("DATACONTRACT_DATABRICKS_TOKEN", "tok")
    monkeypatch.delenv("DATACONTRACT_DATABRICKS_SERVER_HOSTNAME", raising=False)

    class _NoHost:
        type = "databricks"
        host = None
        catalog = None
        schema_ = None

    with pytest.raises(DataContractException) as exc_info:
        to_databricks_soda_configuration(_NoHost())

    assert "DATACONTRACT_DATABRICKS_SERVER_HOSTNAME" in exc_info.value.reason
