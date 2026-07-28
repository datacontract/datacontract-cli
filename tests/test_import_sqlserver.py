"""Tests for the SQL Server importer.

The catalog reads need the ODBC driver, which only CI installs, so those are
gated the same way ``test_test_sqlserver.py`` gates its own — see that file for
the local setup. The argument handling is checked unconditionally, because it
rejects before any connection is opened.
"""

import os

import pytest
from testcontainers.mssql import SqlServerContainer

from datacontract.data_contract import DataContract
from datacontract.model.exceptions import DataContractException
from datacontract.model.run import ResultEnum

# Absolute paths so the module-scoped container fixture (which runs before the
# function-scoped change_test_dir chdir) can find the fixtures from any cwd.
_HERE = os.path.dirname(os.path.abspath(__file__))
SEED = os.path.join(_HERE, "fixtures/sqlserver/data/data.sql")

sql_server = SqlServerContainer()
SQL_SERVER_PORT = 1433

requires_ci = pytest.mark.skipif(not os.getenv("CI"), reason="Skipping test outside CI/CD environment")


@pytest.fixture(scope="module")
def mssql_container(request):
    sql_server.start()
    request.addfinalizer(sql_server.stop)
    _init_sql()


@pytest.fixture
def credentials(monkeypatch):
    monkeypatch.setenv("DATACONTRACT_SQLSERVER_USERNAME", sql_server.username)
    monkeypatch.setenv("DATACONTRACT_SQLSERVER_PASSWORD", sql_server.password)
    monkeypatch.setenv("DATACONTRACT_SQLSERVER_TRUST_SERVER_CERTIFICATE", "True")
    monkeypatch.setenv("DATACONTRACT_SQLSERVER_DRIVER", "ODBC Driver 18 for SQL Server")


def _init_sql():
    import pyodbc

    connection = pyodbc.connect(
        f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={sql_server.get_container_host_ip()},"
        f"{sql_server.get_exposed_port(SQL_SERVER_PORT)};UID={sql_server.username};"
        f"PWD={sql_server.password};TrustServerCertificate=yes",
        autocommit=True,
    )
    with open(SEED) as file:
        for statement in filter(None, (part.strip() for part in file.read().split("GO"))):
            connection.execute(statement)
    connection.close()


def _import(**kwargs):
    kwargs.setdefault("database", "master")
    kwargs.setdefault("port", sql_server.get_exposed_port(SQL_SERVER_PORT))
    return DataContract.import_from_source("sqlserver", sql_server.get_container_host_ip(), **kwargs)


@requires_ci
def test_import_sqlserver(mssql_container, credentials):
    result = _import()

    server = result.servers[0]
    assert (server.type, server.schema_) == ("sqlserver", "dbo")
    assert [prop.property for prop in server.customProperties] == ["driver"]
    assert result.schema_, "expected at least one table"


@requires_ci
def test_imported_contract_passes_test_without_editing(mssql_container, credentials):
    """The point of the native import: import, then test, no hand-editing."""
    result = _import()

    run = DataContract(data_contract_str=result.to_yaml()).test()

    print(run.pretty())
    assert run.result == ResultEnum.passed


@requires_ci
def test_import_sqlserver_produces_a_valid_contract(mssql_container, credentials):
    result = _import()

    assert DataContract(data_contract_str=result.to_yaml()).lint().result == ResultEnum.passed


@requires_ci
def test_import_sqlserver_fails_on_an_unknown_table(mssql_container, credentials):
    with pytest.raises(DataContractException) as exc_info:
        _import(sqlserver_table=["does_not_exist"])

    assert "No tables found" in exc_info.value.reason


# ---------------------------------------------------------------------------
# Argument handling — rejected before a connection is opened, so no driver needed
# ---------------------------------------------------------------------------
def test_import_sqlserver_requires_a_database():
    with pytest.raises(DataContractException) as exc_info:
        DataContract.import_from_source("sqlserver", "localhost", database=None)

    assert "database is required" in exc_info.value.reason


def test_import_sqlserver_requires_a_host():
    with pytest.raises(DataContractException) as exc_info:
        DataContract.import_from_source("sqlserver", None, database="mydb")

    assert "host is required" in exc_info.value.reason
