import logging

import psycopg2
import pytest
from testcontainers.postgres import PostgresContainer

from datacontract.data_contract import DataContract

logging.basicConfig(level=logging.DEBUG, force=True)

datacontract = "fixtures/postgres/datacontract.yaml"
sql_file_path = "fixtures/postgres/data/data.sql"

postgres = PostgresContainer("postgres:16")


@pytest.fixture(scope="module", autouse=True)
def postgres_container(request):
    postgres.start()

    def remove_container():
        postgres.stop()

    request.addfinalizer(remove_container)


def test_test_postgres(postgres_container, monkeypatch):
    monkeypatch.setenv("DATACONTRACT_POSTGRES_USERNAME", postgres.POSTGRES_USER)
    monkeypatch.setenv("DATACONTRACT_POSTGRES_PASSWORD", postgres.POSTGRES_PASSWORD)
    # monkeypatch.setenv("DATACONTRACT_POSTGRES_USERNAME", postgres.username)
    # monkeypatch.setenv("DATACONTRACT_POSTGRES_PASSWORD", postgres.password)
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
    port = postgres.get_exposed_port(5432)
    data_contract_str = data_contract_str.replace("__PORT__", port)
    return data_contract_str


def _init_sql():
    connection = psycopg2.connect(
        database=postgres.POSTGRES_DB,
        user=postgres.POSTGRES_USER,
        password=postgres.POSTGRES_PASSWORD,
        # database=postgres.dbname,
        # user=postgres.username,
        # password=postgres.password,
        host=postgres.get_container_host_ip(),
        port=postgres.get_exposed_port(5432),
    )
    cursor = connection.cursor()
    with open(sql_file_path, "r") as sql_file:
        sql_commands = sql_file.read()
        cursor.execute(sql_commands)
    connection.commit()
    cursor.close()
    connection.close()
