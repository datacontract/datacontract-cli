import clickhouse_connect
import pytest
from testcontainers.community.clickhouse import ClickHouseContainer

from datacontract.data_contract import DataContract
from datacontract.model.run import ResultEnum

clickhouse = ClickHouseContainer("clickhouse/clickhouse-server:25.8", username="dc", password="dcpass")


@pytest.fixture(scope="module", autouse=True)
def clickhouse_container(request):
    clickhouse.start()
    request.addfinalizer(clickhouse.stop)


@pytest.fixture(autouse=True)
def credentials(monkeypatch):
    monkeypatch.setenv("DATACONTRACT_CLICKHOUSE_USERNAME", "dc")
    monkeypatch.setenv("DATACONTRACT_CLICKHOUSE_PASSWORD", "dcpass")


def _client(database: str = "default"):
    return clickhouse_connect.get_client(
        host=clickhouse.get_container_host_ip(),
        port=int(clickhouse.get_exposed_port(8123)),
        username="dc",
        password="dcpass",
        database=database,
    )


def load(database: str, data_file: str) -> None:
    _client().command(f"CREATE DATABASE {database}")
    client = _client(database)
    with open(f"fixtures/clickhouse/data/{data_file}") as file:
        for statement in file.read().split(";"):
            statement = "\n".join(line for line in statement.splitlines() if not line.strip().startswith("--"))
            if statement.strip():
                client.command(statement)


def contract(database: str) -> str:
    with open("fixtures/clickhouse/odcs.yaml") as file:
        return file.read().replace("__PORT__", str(clickhouse.get_exposed_port(8123))).replace("__DATABASE__", database)


def failed_checks(run) -> dict[str, str]:
    return {check.name: check.reason for check in run.checks if check.result != ResultEnum.passed}


def test_valid_data_passes_every_check():
    load("valid", "orders.sql")

    run = DataContract(data_contract_str=contract("valid")).test()

    print(run.pretty())
    assert run.result == ResultEnum.passed
    assert failed_checks(run) == {}
    # one physical type check per column, read from system.columns
    assert len([check for check in run.checks if check.type == "field_physical_type"]) == 11


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
    }


def test_a_physical_type_that_differs_from_the_column_fails():
    load("physical", "orders.sql")
    wrong = (
        contract("physical")
        .replace("physicalType: Int32", "physicalType: Int64")
        .replace("physicalType: LowCardinality(String)", "physicalType: String")
        .replace("physicalType: Decimal(10, 2)", "physicalType: Decimal(12, 2)")
        .replace("physicalType: Array(String)", "physicalType: Array(Int32)")
    )

    run = DataContract(data_contract_str=wrong).test()

    assert failed_checks(run) == {
        "Check that field quantity has physical type Int64": "expected physical type 'Int64' but the column is 'Int32'",
        "Check that field order_status has physical type String": (
            "expected physical type 'String' but the column is 'LowCardinality(String)'"
        ),
        "Check that field order_total has physical type Decimal(12, 2)": (
            "expected physical type 'Decimal(12, 2)' but the column is 'Decimal(10, 2)'"
        ),
        "Check that field tags has physical type Array(Int32)": (
            "expected physical type 'Array(Int32)' but the column is 'Array(String)'"
        ),
    }


def test_sql_standard_spellings_match_the_types_clickhouse_stores():
    """ClickHouse stores a VARCHAR(8) column as String and a TIMESTAMP column as DateTime."""
    load("aliases", "orders.sql")
    aliased = (
        contract("aliases")
        .replace("physicalType: String\n", "physicalType: VARCHAR(8)\n", 1)
        .replace("physicalType: DateTime\n", "physicalType: TIMESTAMP\n")
        .replace("physicalType: DateTime64(3, 'UTC')", "physicalType: DateTime64(3)")
    )
    assert "VARCHAR(8)" in aliased and "TIMESTAMP" in aliased

    run = DataContract(data_contract_str=aliased).test()

    assert failed_checks(run) == {}


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
