"""Unit tests for SQL Server auth-method selection.

These do not open a connection: they assert the kwargs that
``_sqlserver_connection_kwargs`` hands to ``ibis.mssql.connect`` (forwarded to
``pyodbc.connect`` as connection-string attributes) for each authentication mode.
Building the kwargs as a pure function keeps the test independent of the ODBC
driver, which is not loadable on every dev machine.
"""

import pytest
from open_data_contract_standard.model import Server

from datacontract.engines.ibis.connections.connect import _sqlserver_connection_kwargs
from datacontract.model.exceptions import DataContractException

SQLSERVER_ENV_VARS = [
    "DATACONTRACT_SQLSERVER_AUTHENTICATION",
    "DATACONTRACT_SQLSERVER_USERNAME",
    "DATACONTRACT_SQLSERVER_PASSWORD",
    "DATACONTRACT_SQLSERVER_CLIENT_ID",
    "DATACONTRACT_SQLSERVER_CLIENT_SECRET",
    "DATACONTRACT_SQLSERVER_TRUST_SERVER_CERTIFICATE",
    "DATACONTRACT_SQLSERVER_ENCRYPTED_CONNECTION",
    "DATACONTRACT_SQLSERVER_DRIVER",
    "DATACONTRACT_SQLSERVER_TRUSTED_CONNECTION",
]


@pytest.fixture
def env(monkeypatch):
    for name in SQLSERVER_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    return monkeypatch


def _server(**kwargs):
    defaults = dict(type="sqlserver", host="localhost", port=1433, database="testdb", schema="dbo")
    defaults.update(kwargs)
    return Server(**defaults)


def test_default_sql_auth(env):
    env.setenv("DATACONTRACT_SQLSERVER_USERNAME", "sa")
    env.setenv("DATACONTRACT_SQLSERVER_PASSWORD", "secret")

    kwargs = _sqlserver_connection_kwargs(_server())

    assert kwargs["user"] == "sa"
    assert kwargs["password"] == "secret"
    assert "Authentication" not in kwargs
    assert kwargs.get("Trusted_Connection") is None
    assert kwargs["Encrypt"] == "yes"


def test_sql_auth_requires_credentials(env):
    with pytest.raises(DataContractException) as exc:
        _sqlserver_connection_kwargs(_server())
    assert "DATACONTRACT_SQLSERVER_USERNAME" in exc.value.reason


def test_windows_auth(env):
    env.setenv("DATACONTRACT_SQLSERVER_AUTHENTICATION", "windows")

    kwargs = _sqlserver_connection_kwargs(_server())

    assert kwargs["Trusted_Connection"] == "yes"
    assert kwargs["user"] is None
    assert kwargs["password"] is None
    assert "Authentication" not in kwargs


def test_legacy_trusted_connection_means_windows(env):
    env.setenv("DATACONTRACT_SQLSERVER_TRUSTED_CONNECTION", "True")

    kwargs = _sqlserver_connection_kwargs(_server())

    assert kwargs["Trusted_Connection"] == "yes"
    assert kwargs["user"] is None


def test_legacy_trusted_connection_takes_precedence(env):
    env.setenv("DATACONTRACT_SQLSERVER_TRUSTED_CONNECTION", "true")
    env.setenv("DATACONTRACT_SQLSERVER_AUTHENTICATION", "ActiveDirectoryPassword")

    kwargs = _sqlserver_connection_kwargs(_server())

    assert kwargs["Trusted_Connection"] == "yes"
    assert "Authentication" not in kwargs


def test_active_directory_password(env):
    env.setenv("DATACONTRACT_SQLSERVER_AUTHENTICATION", "ActiveDirectoryPassword")
    env.setenv("DATACONTRACT_SQLSERVER_USERNAME", "user@domain.com")
    env.setenv("DATACONTRACT_SQLSERVER_PASSWORD", "ad_secret")

    kwargs = _sqlserver_connection_kwargs(_server())

    assert kwargs["Authentication"] == "ActiveDirectoryPassword"
    assert kwargs["user"] == "user@domain.com"
    assert kwargs["password"] == "ad_secret"


def test_active_directory_service_principal(env):
    env.setenv("DATACONTRACT_SQLSERVER_AUTHENTICATION", "ActiveDirectoryServicePrincipal")
    env.setenv("DATACONTRACT_SQLSERVER_CLIENT_ID", "app-id-123")
    env.setenv("DATACONTRACT_SQLSERVER_CLIENT_SECRET", "app-secret")

    kwargs = _sqlserver_connection_kwargs(_server())

    assert kwargs["Authentication"] == "ActiveDirectoryServicePrincipal"
    assert kwargs["user"] == "app-id-123"
    assert kwargs["password"] == "app-secret"


def test_service_principal_requires_client_id(env):
    env.setenv("DATACONTRACT_SQLSERVER_AUTHENTICATION", "ActiveDirectoryServicePrincipal")
    with pytest.raises(DataContractException) as exc:
        _sqlserver_connection_kwargs(_server())
    assert "DATACONTRACT_SQLSERVER_CLIENT_ID" in exc.value.reason


def test_active_directory_interactive_with_username_hint(env):
    env.setenv("DATACONTRACT_SQLSERVER_AUTHENTICATION", "ActiveDirectoryInteractive")
    env.setenv("DATACONTRACT_SQLSERVER_USERNAME", "user@domain.com")

    kwargs = _sqlserver_connection_kwargs(_server())

    assert kwargs["Authentication"] == "ActiveDirectoryInteractive"
    assert kwargs["user"] == "user@domain.com"
    assert kwargs["password"] is None
    # must not fall back to Windows integrated auth
    assert kwargs["Trusted_Connection"] == "no"


def test_active_directory_interactive_without_username(env):
    env.setenv("DATACONTRACT_SQLSERVER_AUTHENTICATION", "ActiveDirectoryInteractive")

    kwargs = _sqlserver_connection_kwargs(_server())

    assert kwargs["Authentication"] == "ActiveDirectoryInteractive"
    assert kwargs["user"] is None
    assert kwargs["Trusted_Connection"] == "no"


def test_cli_auth_uses_default_credential_chain(env):
    env.setenv("DATACONTRACT_SQLSERVER_AUTHENTICATION", "cli")

    kwargs = _sqlserver_connection_kwargs(_server())

    assert kwargs["Authentication"] == "ActiveDirectoryDefault"
    assert kwargs["user"] is None
    assert kwargs["password"] is None
    assert kwargs["Trusted_Connection"] == "no"


def test_ssl_options(env):
    env.setenv("DATACONTRACT_SQLSERVER_USERNAME", "sa")
    env.setenv("DATACONTRACT_SQLSERVER_PASSWORD", "secret")
    env.setenv("DATACONTRACT_SQLSERVER_TRUST_SERVER_CERTIFICATE", "True")
    env.setenv("DATACONTRACT_SQLSERVER_ENCRYPTED_CONNECTION", "False")

    kwargs = _sqlserver_connection_kwargs(_server())

    assert kwargs["TrustServerCertificate"] == "yes"
    assert kwargs["Encrypt"] == "no"


def test_server_fields_and_driver(env):
    env.setenv("DATACONTRACT_SQLSERVER_USERNAME", "sa")
    env.setenv("DATACONTRACT_SQLSERVER_PASSWORD", "secret")
    env.setenv("DATACONTRACT_SQLSERVER_DRIVER", "ODBC Driver 18 for SQL Server")

    kwargs = _sqlserver_connection_kwargs(_server(host="myserver.database.windows.net", port=1433, database="mydb"))

    assert kwargs["host"] == "myserver.database.windows.net"
    assert kwargs["port"] == 1433
    assert kwargs["database"] == "mydb"
    assert kwargs["driver"] == "ODBC Driver 18 for SQL Server"
