from pathlib import Path

import mysql.connector
import pytest
from testcontainers.mysql import MySqlContainer

from datacontract.data_contract import DataContract
from datacontract.model.run import ResultEnum
from tests.dcs_deprecation import assert_dcs_deprecation_is_the_only_warning, without_dcs_deprecation

mysql_container = MySqlContainer("mysql:8")


@pytest.fixture(scope="module", autouse=True)
def start_mysql_container(request):
    mysql_container.start()

    def remove_container():
        mysql_container.stop()

    request.addfinalizer(remove_container)
    _init_sql(Path(__file__).parent / "fixtures/mysql/data/data.sql")


def test_test_mysql(start_mysql_container, monkeypatch):
    monkeypatch.setenv("DATACONTRACT_MYSQL_USERNAME", mysql_container.username)
    monkeypatch.setenv("DATACONTRACT_MYSQL_PASSWORD", mysql_container.password)

    datacontract_file = "fixtures/mysql/datacontract.yaml"
    data_contract_str = _setup_datacontract(datacontract_file)
    data_contract = DataContract(data_contract_str=data_contract_str)

    run = data_contract.test()

    print(run)
    assert_dcs_deprecation_is_the_only_warning(run)
    assert all(check.result == ResultEnum.passed for check in without_dcs_deprecation(run))


def test_test_mysql_odcs(start_mysql_container, monkeypatch):
    monkeypatch.setenv("DATACONTRACT_MYSQL_USERNAME", mysql_container.username)
    monkeypatch.setenv("DATACONTRACT_MYSQL_PASSWORD", mysql_container.password)

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


def test_catalog_views_are_checked_like_tables(start_mysql_container, monkeypatch):
    monkeypatch.setenv("DATACONTRACT_MYSQL_USERNAME", mysql_container.username)
    monkeypatch.setenv("DATACONTRACT_MYSQL_PASSWORD", mysql_container.password)
    contract = f"""apiVersion: v3.1.0
kind: DataContract
id: mysql-catalog
name: MySQL catalog
version: 1.0.0
status: active
servers:
  - server: catalog
    type: mysql
    host: localhost
    port: {mysql_container.get_exposed_port(3306)}
    database: information_schema
schema:
  - name: TABLES
    quality:
      - type: sql
        description: Every table in the test database uses InnoDB
        query: SELECT COUNT(*) FROM TABLES WHERE TABLE_SCHEMA = 'test' AND ENGINE <> 'InnoDB'
        mustBe: 0
    properties:
      - name: TABLE_NAME
        logicalType: string
        required: true
      - name: TABLE_ROWS
        logicalType: integer
        logicalTypeOptions:
          maximum: 100000000
"""

    run = DataContract(data_contract_str=contract).test()

    assert run.result == "passed", [(c.name, c.reason) for c in run.checks if c.result != "passed"]


def test_a_check_does_not_copy_the_mysql_table(start_mysql_container, monkeypatch):
    """A MAX and a filtered count run on MySQL. The server is not asked for every row."""
    monkeypatch.setenv("DATACONTRACT_MYSQL_USERNAME", mysql_container.username)
    monkeypatch.setenv("DATACONTRACT_MYSQL_PASSWORD", mysql_container.password)
    _seed_bulk_orders()
    _reset_general_log()
    _run_bulk_contract()

    data_sql = [
        sql for sql in _general_log() if "bulk_orders" in sql.lower() and sql.lower().lstrip().startswith("select")
    ]
    assert data_sql
    assert all(_is_pushed_aggregate(sql) for sql in data_sql), data_sql


def _run_bulk_contract():
    port = mysql_container.get_exposed_port(3306)
    contract = f"""apiVersion: v3.1.0
kind: DataContract
id: mysql-bulk
name: Bulk orders
version: 1.0.0
status: active
servers:
  - server: mysql
    type: mysql
    host: localhost
    port: {port}
    database: {mysql_container.dbname}
schema:
  - name: bulk_orders
    properties:
      - name: n
        logicalType: integer
      - name: label
        logicalType: string
    quality:
      - type: sql
        description: highest n
        query: SELECT MAX(n) FROM bulk_orders
        mustBe: 99
      - type: sql
        description: no negative n
        query: SELECT COUNT(*) FROM bulk_orders WHERE n < 0
        mustBe: 0
"""
    run = DataContract(data_contract_str=contract).test()
    assert run.result == "passed", [(c.name, c.reason) for c in run.checks if c.result != "passed"]
    return run


def _seed_bulk_orders():
    connection = mysql.connector.connect(
        database=mysql_container.dbname,
        user=mysql_container.username,
        password=mysql_container.password,
        host=mysql_container.get_container_host_ip(),
        port=int(mysql_container.get_exposed_port(3306)),
    )
    cursor = connection.cursor()
    cursor.execute("DROP TABLE IF EXISTS bulk_orders")
    cursor.execute("CREATE TABLE bulk_orders (n INT NOT NULL, label VARCHAR(16) NOT NULL, PRIMARY KEY (n))")
    cursor.executemany(
        "INSERT INTO bulk_orders (n, label) VALUES (%s, %s)",
        [(i, f"row-{i}") for i in range(100)],
    )
    connection.commit()
    cursor.close()
    connection.close()


def _reset_general_log():
    connection = _root_connection()
    cursor = connection.cursor()
    cursor.execute("SET GLOBAL log_output = 'TABLE'")
    cursor.execute("SET GLOBAL general_log = 'ON'")
    cursor.execute("TRUNCATE TABLE mysql.general_log")
    connection.commit()
    cursor.close()
    connection.close()


def _general_log() -> list[str]:
    connection = _root_connection()
    cursor = connection.cursor()
    cursor.execute(
        "SELECT argument FROM mysql.general_log WHERE command_type IN ('Query', 'Execute') AND argument IS NOT NULL"
    )
    statements = []
    for (argument,) in cursor.fetchall():
        if isinstance(argument, (bytes, bytearray)):
            argument = argument.decode()
        statements.append(argument)
    cursor.close()
    connection.close()
    return statements


def _root_connection():
    return mysql.connector.connect(
        user="root",
        password=mysql_container.root_password,
        host=mysql_container.get_container_host_ip(),
        port=int(mysql_container.get_exposed_port(3306)),
    )


def _is_pushed_aggregate(sql: str) -> bool:
    compact = " ".join(sql.lower().split())
    return any(token in compact for token in ("max(", "min(", "count(", "sum(", "avg("))
