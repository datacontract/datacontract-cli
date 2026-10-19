import logging
import time

import pytest
from impala.dbapi import connect
from testcontainers.core.container import DockerContainer

from datacontract.data_contract import DataContract
from datacontract.model.run import ResultEnum

log = logging.getLogger(__name__)


class HiveContainer(DockerContainer):
    """HiveServer2 with an embedded Derby metastore, on local storage."""

    def __init__(self, image: str = "apache/hive:4.0.1", **kwargs) -> None:
        super().__init__(image, **kwargs)
        self.with_env("SERVICE_NAME", "hiveserver2")
        self.with_exposed_ports(10000)

    def start(self, timeout: int = 180) -> "HiveContainer":
        super().start()
        start = time.time()
        # the port opens long before HiveServer2 accepts sessions
        while True:
            try:
                self.cursor().execute("SHOW DATABASES")
                return self
            except Exception as e:
                log.debug(e)
            if time.time() - start > timeout:
                raise TimeoutError(f"HiveServer2 did not accept a session within {timeout} seconds")
            time.sleep(2)

    def port(self) -> int:
        return int(self.get_exposed_port(10000))

    def cursor(self):
        connection = connect(
            host=self.get_container_host_ip(), port=self.port(), auth_mechanism="PLAIN", user="hive", password="hive"
        )
        return connection.cursor()


hive = HiveContainer()


@pytest.fixture(scope="module", autouse=True)
def hive_container(request):
    hive.start()
    request.addfinalizer(hive.stop)


def load(database: str, data_file: str) -> None:
    cursor = hive.cursor()
    cursor.execute(f"CREATE DATABASE {database}")
    cursor.execute(f"USE {database}")
    with open(f"fixtures/hive/data/{data_file}") as file:
        for statement in file.read().split(";"):
            statement = "\n".join(line for line in statement.splitlines() if not line.strip().startswith("--"))
            if statement.strip():
                cursor.execute(statement)


def contract(database: str) -> str:
    with open("fixtures/hive/odcs.yaml") as file:
        return file.read().replace("__PORT__", str(hive.port())).replace("__DATABASE__", database)


def failed_checks(run) -> dict[str, str]:
    return {check.name: check.reason for check in run.checks if check.result != ResultEnum.passed}


def test_valid_data_passes_every_check():
    load("valid", "orders.sql")

    run = DataContract(data_contract_str=contract("valid")).test()

    print(run.pretty())
    assert run.result == ResultEnum.passed
    assert failed_checks(run) == {}
    # one physical type check per column, the partition column included
    assert len([check for check in run.checks if check.type == "field_physical_type"]) == 15


def test_each_violation_fails_its_check():
    load("invalid", "orders_invalid.sql")

    run = DataContract(data_contract_str=contract("invalid")).test()

    print(run.pretty())
    assert run.result == ResultEnum.failed
    assert failed_checks(run) == {
        "Check that unique field order_id has no duplicate values": "Actual duplicate_count(order_id) was 1, expected = 0",
        "Check that field order_id matches regex pattern ^ORD-\\d{4}$": "Actual invalid_count(order_id) was 1, expected = 0",
        "Check that field customer_id has missing_count < 2": "Actual missing_count(customer_id) was 2, expected < 2",
        "Check that field order_status has invalid_count = 0": "Actual invalid_count(order_status) was 1, expected = 0",
        "Check that field order_total has a minimum of 0": "Actual invalid_count(order_total) was 1, expected = 0",
        "Check that field quantity has a minimum of 1": "Actual invalid_count(quantity) was 1, expected = 0",
        "Check that model orders has duplicate_count = 0 for columns order_id": (
            "Actual duplicate_count(orders) was 1, expected = 0"
        ),
        "No order has a negative total": "Actual custom_sql(orders) was 1, expected = 0",
        "Every order id follows the ORD-nnnn scheme": "Actual custom_sql(orders) was 1, expected = 0",
    }


def test_a_physical_type_that_differs_from_the_column_fails():
    load("physical", "orders.sql")
    wrong = (
        contract("physical")
        .replace("physicalType: varchar(10)", "physicalType: varchar(20)")
        .replace("physicalType: bigint", "physicalType: int")
        .replace("physicalType: array<string>", "physicalType: array<int>")
        .replace("physicalType: struct<city:string,zip:string>", "physicalType: struct<city:string,postcode:string>")
    )

    run = DataContract(data_contract_str=wrong).test()

    assert failed_checks(run) == {
        "Check that field customer_id has physical type varchar(20)": (
            "expected physical type 'varchar(20)' but the column is 'varchar(10)'"
        ),
        "Check that field line_count has physical type int": "expected physical type 'int' but the column is 'bigint'",
        "Check that field tags has physical type array<int>": (
            "expected physical type 'array<int>' but the column is 'array<string>'"
        ),
        "Check that field shipping has physical type struct<city:string,postcode:string>": (
            "expected physical type 'struct<city:string,postcode:string>' but the column is "
            "'struct<city:string,zip:string>'"
        ),
    }


def test_a_row_filter_restricts_the_row_checks():
    load("filtered", "orders_invalid.sql")

    run = DataContract(data_contract_str=contract("filtered"), filter="order_id LIKE 'ORD-%'").test()

    failed = failed_checks(run)
    # the malformed, negative and zero-quantity order is filtered out ...
    assert "Check that field order_id matches regex pattern ^ORD-\\d{4}$" not in failed
    assert "Check that field quantity has a minimum of 1" not in failed
    # ... while the duplicated order id is still there
    assert "Check that unique field order_id has no duplicate values" in failed
    assert run.filters == {"orders": "order_id LIKE 'ORD-%'"}


def test_failed_rows_are_sampled():
    load("samples", "orders_invalid.sql")

    run = DataContract(data_contract_str=contract("samples"), include_failed_samples=True).test()

    regex = next(check for check in run.checks if check.name.startswith("Check that field order_id matches regex"))
    assert regex.failedSamples == [{"order_id": "order-3"}]
