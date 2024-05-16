import logging
from typing import Literal

import pymssql
import pytest
from testcontainers.mssql import SqlServerContainer

from datacontract.data_contract import DataContract

logging.basicConfig(level=logging.DEBUG, force=True)

datacontract = "fixtures/sqlserver/datacontract.yaml"
sql_file_path = "fixtures/sqlserver/data/data.sql"

sql_server = SqlServerContainer()
SQL_SERVER_PORT: int = 1433

@pytest.fixture(scope="module", autouse=True)
def mssql_container(request):
    sql_server.start()

    def remove_container():
        sql_server.stop()

    request.addfinalizer(remove_container)


def test_test_sqlserver(mssql_container, monkeypatch):
    monkeypatch.setenv("DATACONTRACT_SQLSERVER_USERNAME", sql_server.SQLSERVER_USER)
    monkeypatch.setenv("DATACONTRACT_SQLSERVER_PASSWORD", sql_server.SQLSERVER_PASSWORD)
    monkeypatch.setenv("DATACONTRACT_TRUST_SERVER_CERTIFICATE", "True")

    _init_sql()

    data_contract_str = _setup_datacontract()
    data_contract = DataContract(data_contract_str=data_contract_str)

    run = data_contract.test()

    print(run)
    assert run.result == "passed"
    assert all(check.result == "passed" for check in run.checks)


def _setup_datacontract():
    with open(datacontract) as data_contract_file:
        data_contract_str = data_contract_file.read()
    port = sql_server.get_exposed_port(SQL_SERVER_PORT)
    data_contract_str = data_contract_str.replace("__PORT__", port)
    return data_contract_str


def _init_sql():
    connection = pymssql.connect(
        database=sql_server.SQLSERVER_DBNAME,
        user=sql_server.SQLSERVER_USER,
        password=sql_server.SQLSERVER_PASSWORD,
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
