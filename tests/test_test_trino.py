import logging

import pytest
from testcontainers.core.container import DockerContainer
from testcontainers.core.waiting_utils import wait_for_logs
from trino.dbapi import connect

from datacontract.data_contract import DataContract

logging.basicConfig(level=logging.DEBUG, force=True)

datacontract = "fixtures/trino/datacontract.yaml"


class TrinoContainer(DockerContainer):
    def __init__(self, image: str = "trinodb/trino:450", **kwargs) -> None:  # noqa: ANN003
        super().__init__(image, **kwargs)
        self.with_exposed_ports(8080)

    def start(self, timeout: int = 30) -> "TrinoContainer":
        """Start the docker container and wait for it to be ready."""
        super().start()
        wait_for_logs(self, predicate="======== SERVER STARTED ========", timeout=timeout)
        return self


trino = TrinoContainer()


@pytest.fixture(scope="module", autouse=True)
def trino_container(request):
    trino.start()

    def remove_container():
        trino.stop()

    request.addfinalizer(remove_container)


def test_test_trino(trino_container, monkeypatch):
    _prepare_table()

    monkeypatch.setenv("DATACONTRACT_TRINO_USERNAME", "my_user")
    monkeypatch.setenv("DATACONTRACT_TRINO_PASSWORD", "")

    data_contract_str = _setup_datacontract()
    data_contract = DataContract(data_contract_str=data_contract_str)

    run = data_contract.test()

    assert run.result == "passed"
    assert all(check.result == "passed" for check in run.checks)


def _prepare_table():
    conn = connect(host="localhost", port=trino.get_exposed_port(8080), user="my_user", catalog="memory")
    cursor = conn.cursor()
    cursor.execute("CREATE SCHEMA IF NOT EXISTS my_schema")
    with open("fixtures/trino/data/table.sql", "r") as sql_file:
        cursor.execute(sql_file.read())
    with open("fixtures/trino/data/data.sql", "r") as sql_file:
        cursor.execute(sql_file.read())


def _setup_datacontract():
    with open(datacontract) as data_contract_file:
        data_contract_str = data_contract_file.read()
    port = trino.get_exposed_port(8080)
    data_contract_str = data_contract_str.replace("__PORT__", port)
    return data_contract_str
