import yaml
from open_data_contract_standard.model import Server

from datacontract.engines.soda.connections.sqlserver import to_sqlserver_soda_configuration


def _make_server(**kwargs):
    defaults = {
        "type": "sqlserver",
        "host": "localhost",
        "port": 1433,
        "database": "testdb",
        "schema": "dbo",
    }
    defaults.update(kwargs)
    return Server(**defaults)


def test_default_sql_auth(monkeypatch):
    monkeypatch.setenv("DATACONTRACT_SQLSERVER_USERNAME", "sa")
    monkeypatch.setenv("DATACONTRACT_SQLSERVER_PASSWORD", "secret")
    monkeypatch.delenv("DATACONTRACT_SQLSERVER_AUTHENTICATION", raising=False)
    monkeypatch.delenv("DATACONTRACT_SQLSERVER_TRUSTED_CONNECTION", raising=False)

    result = yaml.safe_load(to_sqlserver_soda_configuration(_make_server()))
    ds = result["data_source sqlserver"]

    assert ds["authentication"] == "sql"
    assert ds["username"] == "sa"
    assert ds["password"] == "secret"
    assert ds["trusted_connection"] is False


def test_active_directory_password(monkeypatch):
    monkeypatch.setenv("DATACONTRACT_SQLSERVER_AUTHENTICATION", "ActiveDirectoryPassword")
    monkeypatch.setenv("DATACONTRACT_SQLSERVER_USERNAME", "user@domain.com")
    monkeypatch.setenv("DATACONTRACT_SQLSERVER_PASSWORD", "ad_secret")
    monkeypatch.delenv("DATACONTRACT_SQLSERVER_TRUSTED_CONNECTION", raising=False)

    result = yaml.safe_load(to_sqlserver_soda_configuration(_make_server()))
    ds = result["data_source sqlserver"]

    assert ds["authentication"] == "activedirectorypassword"
    assert ds["username"] == "user@domain.com"
    assert ds["password"] == "ad_secret"


def test_active_directory_service_principal(monkeypatch):
    monkeypatch.setenv("DATACONTRACT_SQLSERVER_AUTHENTICATION", "ActiveDirectoryServicePrincipal")
    monkeypatch.setenv("DATACONTRACT_SQLSERVER_CLIENT_ID", "app-id-123")
    monkeypatch.setenv("DATACONTRACT_SQLSERVER_CLIENT_SECRET", "app-secret")
    monkeypatch.delenv("DATACONTRACT_SQLSERVER_TRUSTED_CONNECTION", raising=False)

    result = yaml.safe_load(to_sqlserver_soda_configuration(_make_server()))
    ds = result["data_source sqlserver"]

    assert ds["authentication"] == "activedirectoryserviceprincipal"
    assert ds["client_id"] == "app-id-123"
    assert ds["client_secret"] == "app-secret"


def test_cli_auth(monkeypatch):
    monkeypatch.setenv("DATACONTRACT_SQLSERVER_AUTHENTICATION", "cli")
    monkeypatch.delenv("DATACONTRACT_SQLSERVER_TRUSTED_CONNECTION", raising=False)

    result = yaml.safe_load(to_sqlserver_soda_configuration(_make_server()))
    ds = result["data_source sqlserver"]

    assert ds["authentication"] == "cli"
    assert ds["trusted_connection"] is False


def test_windows_auth(monkeypatch):
    monkeypatch.setenv("DATACONTRACT_SQLSERVER_AUTHENTICATION", "windows")
    monkeypatch.delenv("DATACONTRACT_SQLSERVER_TRUSTED_CONNECTION", raising=False)

    result = yaml.safe_load(to_sqlserver_soda_configuration(_make_server()))
    ds = result["data_source sqlserver"]

    assert ds["authentication"] == "sql"
    assert ds["trusted_connection"] is True


def test_legacy_trusted_connection(monkeypatch):
    monkeypatch.setenv("DATACONTRACT_SQLSERVER_TRUSTED_CONNECTION", "True")
    monkeypatch.delenv("DATACONTRACT_SQLSERVER_AUTHENTICATION", raising=False)

    result = yaml.safe_load(to_sqlserver_soda_configuration(_make_server()))
    ds = result["data_source sqlserver"]

    assert ds["authentication"] == "sql"
    assert ds["trusted_connection"] is True


def test_all_env_vars(monkeypatch):
    monkeypatch.setenv("DATACONTRACT_SQLSERVER_USERNAME", "user")
    monkeypatch.setenv("DATACONTRACT_SQLSERVER_PASSWORD", "pass")
    monkeypatch.setenv("DATACONTRACT_SQLSERVER_TRUST_SERVER_CERTIFICATE", "True")
    monkeypatch.setenv("DATACONTRACT_SQLSERVER_ENCRYPTED_CONNECTION", "False")
    monkeypatch.setenv("DATACONTRACT_SQLSERVER_DRIVER", "ODBC Driver 18 for SQL Server")
    monkeypatch.delenv("DATACONTRACT_SQLSERVER_AUTHENTICATION", raising=False)
    monkeypatch.delenv("DATACONTRACT_SQLSERVER_TRUSTED_CONNECTION", raising=False)

    result = yaml.safe_load(to_sqlserver_soda_configuration(_make_server()))
    ds = result["data_source sqlserver"]

    assert ds["username"] == "user"
    assert ds["password"] == "pass"
    assert ds["trust_server_certificate"] == "True"
    assert ds["encrypt"] == "False"
    assert ds["driver"] == "ODBC Driver 18 for SQL Server"
    assert ds["authentication"] == "sql"


def test_server_fields_from_contract(monkeypatch):
    monkeypatch.delenv("DATACONTRACT_SQLSERVER_AUTHENTICATION", raising=False)
    monkeypatch.delenv("DATACONTRACT_SQLSERVER_TRUSTED_CONNECTION", raising=False)

    server = _make_server(host="myserver.database.windows.net", port=1433, database="mydb", schema="myschema")
    result = yaml.safe_load(to_sqlserver_soda_configuration(server))
    ds = result["data_source sqlserver"]

    assert ds["host"] == "myserver.database.windows.net"
    assert ds["port"] == "1433"
    assert ds["database"] == "mydb"
    assert ds["schema"] == "myschema"
