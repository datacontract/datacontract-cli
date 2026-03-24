import mysql.connector
import pytest
from testcontainers.mysql import MySqlContainer

from datacontract.data_contract import DataContract
from datacontract.model.run import ResultEnum

mysql_container = MySqlContainer("mysql:8")


@pytest.fixture(scope="function", autouse=True)
def start_mysql_container(request):
    mysql_container.start()

    def remove_container():
        mysql_container.stop()

    request.addfinalizer(remove_container)


def test_test_mysql(start_mysql_container, monkeypatch):
    monkeypatch.setenv("DATACONTRACT_MYSQL_USERNAME", mysql_container.username)
    monkeypatch.setenv("DATACONTRACT_MYSQL_PASSWORD", mysql_container.password)
    _init_sql("fixtures/mysql/data/data.sql")

    datacontract_file = "fixtures/mysql/datacontract.yaml"
    data_contract_str = _setup_datacontract(datacontract_file)
    data_contract = DataContract(data_contract_str=data_contract_str)

    run = data_contract.test()

    print(run)
    assert run.result == "passed"
    assert all(check.result == ResultEnum.passed for check in run.checks)


def test_test_mysql_odcs(start_mysql_container, monkeypatch):
    monkeypatch.setenv("DATACONTRACT_MYSQL_USERNAME", mysql_container.username)
    monkeypatch.setenv("DATACONTRACT_MYSQL_PASSWORD", mysql_container.password)
    _init_sql("fixtures/mysql/data/data.sql")

    datacontract_file = "fixtures/mysql/odcs.yaml"
    data_contract_str = _setup_datacontract(datacontract_file)
    data_contract = DataContract(data_contract_str=data_contract_str)

    run = data_contract.test()

    print(run.pretty())
    assert run.result == "passed"
    assert all(check.result == "passed" for check in run.checks)


def _setup_datacontract(file):
    with open(file) as data_contract_file:
        data_contract_str = data_contract_file.read()
    port = mysql_container.get_exposed_port(3306)
    data_contract_str = data_contract_str.replace("3306", str(port))
    return data_contract_str


def _init_sql(file_path):
    connection = mysql.connector.connect(
        database=mysql_container.dbname,
        user=mysql_container.username,
        password=mysql_container.password,
        host=mysql_container.get_container_host_ip(),
        port=int(mysql_container.get_exposed_port(3306)),
    )
    cursor = connection.cursor()
    with open(file_path, "r") as sql_file:
        sql_commands = sql_file.read()
        for statement in sql_commands.split(";"):
            statement = statement.strip()
            if statement:
                cursor.execute(statement)
    connection.commit()
    cursor.close()
    connection.close()
