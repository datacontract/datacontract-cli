import logging
import time
from pathlib import Path

import pytest
from impala.dbapi import connect
from testcontainers.core.container import DockerContainer

from datacontract.data_contract import DataContract
from datacontract.model.exceptions import DataContractException
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


@pytest.fixture(scope="module")
def valid_orders():
    load("valid", "orders.sql")
    return "valid"


@pytest.fixture(scope="module")
def invalid_orders():
    load("invalid", "orders_invalid.sql")
    return "invalid"


def load(database: str, data_file: str) -> None:
    cursor = hive.cursor()
    cursor.execute(f"CREATE DATABASE {database}")
    cursor.execute(f"USE {database}")
    with open(Path(__file__).parent / "fixtures/hive/data" / data_file) as file:
        for statement in file.read().split(";"):
            statement = "\n".join(line for line in statement.splitlines() if not line.strip().startswith("--"))
            if statement.strip():
                cursor.execute(statement)


def contract(database: str) -> str:
    with open("fixtures/hive/odcs.yaml") as file:
        return file.read().replace("__PORT__", str(hive.port())).replace("__DATABASE__", database)


def failed_checks(run) -> dict[str, str]:
    return {check.name: check.reason for check in run.checks if check.result != ResultEnum.passed}


def test_valid_data_passes_every_check(valid_orders):
    run = DataContract(data_contract_str=contract(valid_orders)).test()

    print(run.pretty())
    assert run.result == ResultEnum.passed
    assert failed_checks(run) == {}
    # one physical type check per column, the partition column included
    assert len([check for check in run.checks if check.type == "field_physical_type"]) == 15


def test_each_violation_fails_its_check(invalid_orders):
    run = DataContract(data_contract_str=contract(invalid_orders)).test()

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


def test_a_physical_type_that_differs_from_the_column_fails(valid_orders):
    wrong = (
        contract(valid_orders)
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


def test_a_row_filter_restricts_the_row_checks(invalid_orders):
    run = DataContract(data_contract_str=contract(invalid_orders), filter="order_id LIKE 'ORD-%'").test()

    failed = failed_checks(run)
    # the malformed, negative and zero-quantity order is filtered out ...
    assert "Check that field order_id matches regex pattern ^ORD-\\d{4}$" not in failed
    assert "Check that field quantity has a minimum of 1" not in failed
    # ... while the duplicated order id is still there
    assert "Check that unique field order_id has no duplicate values" in failed
    assert run.filters == {"orders": "order_id LIKE 'ORD-%'"}


def test_failed_rows_are_sampled(invalid_orders):
    run = DataContract(data_contract_str=contract(invalid_orders), include_failed_samples=True).test()

    regex = next(check for check in run.checks if check.name.startswith("Check that field order_id matches regex"))
    assert regex.failedSamples == [{"order_id": "order-3"}]


DATABASE = "shop"

SEED = [
    f"CREATE DATABASE {DATABASE}",
    f"""CREATE TABLE {DATABASE}.orders (
          order_id STRING COMMENT 'The order',
          customer_id VARCHAR(36),
          order_total DECIMAL(10,2),
          line_count INT,
          ordered_at TIMESTAMP,
          tags ARRAY<STRING>,
          shipping STRUCT<city:STRING,zip:STRING>,
          attributes MAP<STRING,BIGINT>
        )
        COMMENT 'One row per order'
        PARTITIONED BY (order_day DATE)
        STORED AS PARQUET""",
    f"""INSERT INTO {DATABASE}.orders PARTITION (order_day = '2026-09-01')
        SELECT 'ORD-1', 'C-1', 50.00, 2, TIMESTAMP '2026-09-01 10:00:00', array('a'),
               named_struct('city', 'Berlin', 'zip', '10115'), map('k', CAST(1 AS BIGINT))""",
    f"CREATE TABLE {DATABASE}.customers (id BIGINT)",
    f"CREATE VIEW {DATABASE}.open_orders AS SELECT order_id FROM {DATABASE}.orders",
]


@pytest.fixture(scope="module")
def hive_server():
    cursor = hive.cursor()
    for statement in SEED:
        cursor.execute(statement)


def _import(**kwargs):
    kwargs.setdefault("database", DATABASE)
    return DataContract.import_from_source("hive", source=hive.get_container_host_ip(), port=hive.port(), **kwargs)


def _properties(odcs, schema_name="orders"):
    schema = next(s for s in odcs.schema_ if s.name == schema_name)
    return {p.name: p for p in schema.properties}


def test_import_hive_takes_the_declared_type_verbatim(hive_server):
    properties = _properties(_import(hive_table=["orders"]))

    assert {name: (p.physicalType, p.logicalType) for name, p in properties.items()} == {
        "order_id": ("string", "string"),
        "customer_id": ("varchar(36)", "string"),
        "order_total": ("decimal(10,2)", "number"),
        "line_count": ("int", "integer"),
        "ordered_at": ("timestamp", "timestamp"),
        "tags": ("array", "array"),
        "shipping": ("struct", "object"),
        "attributes": ("map", "map"),
        # the partition column, which Hive lists in its own section
        "order_day": ("date", "date"),
    }
    assert properties["tags"].items.logicalType == "string"
    assert [p.name for p in properties["shipping"].properties] == ["city", "zip"]
    assert properties["attributes"].map.value.logicalType == "integer"


def test_comments_become_descriptions(hive_server):
    odcs = _import(hive_table=["orders"])

    assert odcs.schema_[0].description == "One row per order"
    assert _properties(odcs)["order_id"].description == "The order"


def test_the_server_is_the_one_imported_from(hive_server):
    server = _import(hive_table=["orders"]).servers[0]

    assert (server.type, server.host, server.port, server.database) == (
        "hive",
        hive.get_container_host_ip(),
        hive.port(),
        DATABASE,
    )


def test_imported_contract_passes_test_without_editing(hive_server):
    odcs = _import()

    run = DataContract(data_contract_str=odcs.to_yaml()).test()

    print(run.pretty())
    assert run.result == ResultEnum.passed
    assert all(check.result == ResultEnum.passed for check in run.checks)
    # nested native types are read from the column's full type
    assert any(c.field == "shipping.city" and c.type == "field_physical_type" for c in run.checks)


def test_import_hive_produces_a_valid_contract(hive_server):
    run = DataContract(data_contract_str=_import().to_yaml()).lint()

    assert run.result == ResultEnum.passed


def test_import_hive_imports_all_tables_and_views_by_default(hive_server):
    odcs = _import()

    assert {s.name: s.physicalType for s in odcs.schema_} == {
        "customers": "table",
        "open_orders": "view",
        "orders": "table",
    }


def test_table_names_are_matched_case_insensitively(hive_server):
    assert [s.name for s in _import(hive_table=["ORDERS"]).schema_] == ["orders"]


def test_import_hive_fails_on_an_unknown_table(hive_server):
    with pytest.raises(DataContractException, match="No tables found"):
        _import(hive_table=["no_such_table"])


def test_import_hive_requires_a_database():
    with pytest.raises(DataContractException, match="--database"):
        DataContract.import_from_source("hive", source="localhost")


def test_import_hive_requires_a_host():
    with pytest.raises(DataContractException, match="--source"):
        DataContract.import_from_source("hive", source=None, database=DATABASE)


def test_describe_formatted_of_older_hive_versions_is_read():
    """Hive 2 and 3 put a `# col_name` header and a blank line before the columns."""
    from datacontract.imports.hive_importer import _create_schema

    rows = [
        ("# col_name            ", "data_type           ", "comment             "),
        ("", None, None),
        ("order_id              ", "string              ", "The order           "),
        ("order_total           ", "decimal(10,2)       ", ""),
        ("", None, None),
        ("# Partition Information", None, None),
        ("# col_name            ", "data_type           ", "comment             "),
        ("", None, None),
        ("order_day             ", "date                ", ""),
        ("", None, None),
        ("# Detailed Table Information", None, None),
        ("Database:           ", "shop                ", None),
        ("Table Type:         ", "MANAGED_TABLE       ", None),
        ("Table Parameters:", None, None),
        ("", "comment             ", "One row per order   "),
        ("", "numFiles            ", "1                   "),
        ("", None, None),
        ("# Storage Information", None, None),
        ("SerDe Library:      ", "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe", None),
    ]

    schema = _create_schema("orders", rows)

    assert [(p.name, p.physicalType, p.description) for p in schema.properties] == [
        ("order_id", "string", "The order"),
        ("order_total", "decimal(10,2)", None),
        ("order_day", "date", None),
    ]
    assert (schema.physicalType, schema.description) == ("table", "One row per order")
