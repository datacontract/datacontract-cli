import logging
import time

import pytest
from testcontainers.core.container import DockerContainer
from trino.dbapi import connect

from datacontract.data_contract import DataContract

# logging.basicConfig(level=logging.DEBUG, force=True)

datacontract = "fixtures/trino/datacontract.yaml"

log = logging.getLogger(__name__)


class TrinoContainer(DockerContainer):
    def __init__(self, image: str = "trinodb/trino:450", **kwargs) -> None:
        super().__init__(image, **kwargs)
        self.with_exposed_ports(8080)

    def start(self, timeout: int = 60) -> "TrinoContainer":
        """Start the docker container and wait for it to be ready."""
        super().start()
        self.wait_for_nodes(timeout)
        return self

    def wait_for_nodes(self, timeout: int):
        interval = 1
        start = time.time()

        # we wait if we can actually retrieve data from the catalog, just waiting for logs seems not sufficient
        while True:
            duration = time.time() - start

            try:
                conn = connect(host="localhost", port=self.get_exposed_port(8080), user="my_user", catalog="memory")
                cursor = conn.cursor()
                cursor.execute("CREATE SCHEMA IF NOT EXISTS __testcontainers__")
                cursor.execute("CREATE TABLE IF NOT EXISTS __testcontainers__.my_table (my_field VARCHAR)")
                cursor.execute("INSERT INTO __testcontainers__.my_table (my_field) values ('test')")

                # a SELECT errors with NO_NODES_AVAILABLE when trino is not ready yet
                cursor.execute("SELECT * from __testcontainers__.my_table")
                cursor.fetchall()

                return duration
            except Exception as e:
                log.debug(e)

            if timeout and duration > timeout:
                raise TimeoutError("container did not return startup test data in %.3f seconds" % timeout)
            time.sleep(interval)


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
