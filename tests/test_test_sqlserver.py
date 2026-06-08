import os

import pytest
from testcontainers.mssql import SqlServerContainer

from datacontract.data_contract import DataContract

# logging.basicConfig(level=logging.DEBUG, force=True)

# Absolute paths so the module-scoped container fixture (which runs before the
# function-scoped change_test_dir chdir) can find the fixtures from any cwd.
_HERE = os.path.dirname(os.path.abspath(__file__))
datacontract = os.path.join(_HERE, "fixtures/sqlserver/datacontract.yaml")
sql_file_path = os.path.join(_HERE, "fixtures/sqlserver/data/data.sql")

sql_server = SqlServerContainer()
SQL_SERVER_PORT: int = 1433


@pytest.fixture(scope="module", autouse=True)
def mssql_container(request):
    sql_server.start()
    _init_sql()

    def remove_container():
        sql_server.stop()

    request.addfinalizer(remove_container)


def _set_sqlserver_env(monkeypatch):
    monkeypatch.setenv("DATACONTRACT_SQLSERVER_USERNAME", sql_server.username)
    monkeypatch.setenv("DATACONTRACT_SQLSERVER_PASSWORD", sql_server.password)
    monkeypatch.setenv("DATACONTRACT_SQLSERVER_TRUST_SERVER_CERTIFICATE", "True")
    monkeypatch.setenv("DATACONTRACT_SQLSERVER_DRIVER", "ODBC Driver 18 for SQL Server")


# To run this on ARM macs, run these commands (https://github.com/pymssql/pymssql/issues/769)
# brew install FreeTDS
# export LDFLAGS="-L/opt/homebrew/lib -L/opt/homebrew/opt/openssl/lib"
# export CFLAGS="-I/opt/homebrew/include"
# export CPPFLAGS="-I/opt/homebrew/opt/openssl@3/include"
# pip uninstall pymssql -y
# pip install pymssql==2.2.8 --no-binary :all:
@pytest.mark.skipif(not os.getenv("CI"), reason="Skipping test outside CI/CD environment")
def test_test_sqlserver(mssql_container, monkeypatch):
    _set_sqlserver_env(monkeypatch)

    data_contract_str = _setup_datacontract()
    data_contract = DataContract(data_contract_str=data_contract_str)

    run = data_contract.test()

    print(run)
    assert run.result == "passed"
    assert all(check.result == "passed" for check in run.checks)


@pytest.mark.skipif(not os.getenv("CI"), reason="Skipping test outside CI/CD environment")
def test_test_sqlserver_pattern_detects_violations(mssql_container, monkeypatch):
    # Regression for #1284: a logicalTypeOptions.pattern check must run on SQL
    # Server (no native regex) via the PATINDEX fallback and actually evaluate
    # the data, rather than failing with "Compilation rule for RegexSearch
    # operation is not defined". field_one values look like "CX-263-DU", so a
    # pattern requiring four consecutive digits matches none of them.
    _set_sqlserver_env(monkeypatch)

    data_contract_str = _setup_datacontract().replace(
        "[A-Z][A-Z]-[0-9][0-9][0-9]-[A-Z][A-Z]",
        "[0-9][0-9][0-9][0-9]",
    )
    data_contract = DataContract(data_contract_str=data_contract_str)

    run = data_contract.test()

    print(run)
    assert run.result == "failed"
    pattern_checks = [c for c in run.checks if c.field == "field_one" and "pattern" in (c.name or "").lower()]
    assert pattern_checks, "expected a pattern check on field_one"
    for check in pattern_checks:
        # The check must fail because rows violate the pattern, not because the
        # backend could not compile the regex.
        assert check.result == "failed"
        assert "RegexSearch" not in (check.reason or "")
        assert "Compilation rule" not in (check.reason or "")


def _setup_datacontract():
    with open(datacontract) as data_contract_file:
        data_contract_str = data_contract_file.read()
    port = sql_server.get_exposed_port(SQL_SERVER_PORT)
    data_contract_str = data_contract_str.replace("__PORT__", str(port))
    return data_contract_str


def _init_sql():
    # import locally as a top level import of pymssql fails on ARM macs
    import pymssql

    connection = pymssql.connect(
        database=sql_server.dbname,
        user=sql_server.username,
        password=sql_server.password,
        host=sql_server.get_container_host_ip(),
        port=sql_server.get_exposed_port(SQL_SERVER_PORT),
    )
    cursor = connection.cursor()
    with open(sql_file_path, "r") as sql_file:
        sql_commands = sql_file.read()
        cursor.execute(sql_commands)
    connection.commit()
    cursor.close()
    connection.close()
