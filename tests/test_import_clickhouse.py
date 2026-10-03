"""Tests for the ClickHouse importer, run against a real ClickHouse container."""

import clickhouse_connect
import pytest
from testcontainers.community.clickhouse import ClickHouseContainer

from datacontract.data_contract import DataContract
from datacontract.imports.clickhouse_importer import map_clickhouse_type
from datacontract.model.exceptions import DataContractException
from datacontract.model.run import ResultEnum

DATABASE = "shop"

SEED = [
    f"CREATE DATABASE {DATABASE}",
    f"""CREATE TABLE {DATABASE}.orders (
          order_id String COMMENT 'The order',
          customer_id Nullable(String),
          status LowCardinality(String),
          order_total Decimal(10, 2),
          line_count UInt16,
          ordered_at DateTime64(3, 'UTC'),
          order_day Date32,
          id UUID,
          tags Array(Nullable(String)),
          attributes Map(String, Int32),
          kind Enum8('retail' = 1, 'wholesale' = 2)
        ) ENGINE = MergeTree ORDER BY (order_id, ordered_at) COMMENT 'One row per order'""",
    f"""INSERT INTO {DATABASE}.orders VALUES
          ('ORD-1', 'C-1', 'open', 50.00, 2, now64(3), today(), generateUUIDv4(), ['a', NULL], {{'k': 1}}, 'retail')""",
    f"CREATE TABLE {DATABASE}.customers (id Int64) ENGINE = MergeTree ORDER BY id",
    f"CREATE VIEW {DATABASE}.open_orders AS SELECT order_id FROM {DATABASE}.orders WHERE status = 'open'",
]

clickhouse = ClickHouseContainer("clickhouse/clickhouse-server:25.8", username="dc", password="dcpass")


@pytest.fixture(scope="module")
def clickhouse_server(request):
    clickhouse.start()
    request.addfinalizer(clickhouse.stop)
    client = clickhouse_connect.get_client(
        host=clickhouse.get_container_host_ip(), port=_port(), username="dc", password="dcpass"
    )
    for statement in SEED:
        client.command(statement)


@pytest.fixture
def credentials(monkeypatch):
    monkeypatch.setenv("DATACONTRACT_CLICKHOUSE_USERNAME", "dc")
    monkeypatch.setenv("DATACONTRACT_CLICKHOUSE_PASSWORD", "dcpass")


def _port():
    return int(clickhouse.get_exposed_port(8123))


def _import(**kwargs):
    kwargs.setdefault("database", DATABASE)
    return DataContract.import_from_source(
        "clickhouse", source=clickhouse.get_container_host_ip(), port=_port(), **kwargs
    )


def _properties(odcs, schema_name="orders"):
    schema = next(s for s in odcs.schema_ if s.name == schema_name)
    return {p.name: p for p in schema.properties}


def test_import_clickhouse_takes_the_declared_type_verbatim(clickhouse_server, credentials):
    odcs = _import(clickhouse_table=["orders"])

    properties = _properties(odcs)
    assert {name: (p.physicalType, p.logicalType) for name, p in properties.items()} == {
        "order_id": ("String", "string"),
        "customer_id": ("Nullable(String)", "string"),
        "status": ("LowCardinality(String)", "string"),
        "order_total": ("Decimal(10, 2)", "number"),
        "line_count": ("UInt16", "integer"),
        "ordered_at": ("DateTime64(3, 'UTC')", "timestamp"),
        "order_day": ("Date32", "date"),
        "id": ("UUID", "string"),
        "tags": ("Array(Nullable(String))", "array"),
        "attributes": ("Map(String, Int32)", "map"),
        "kind": ("Enum8('retail' = 1, 'wholesale' = 2)", "string"),
    }
    assert (properties["tags"].items.physicalType, properties["tags"].items.logicalType) == ("String", "string")
    assert properties["attributes"].map.value.logicalType == "integer"


def test_only_nullable_columns_are_optional(clickhouse_server, credentials):
    properties = _properties(_import(clickhouse_table=["orders"]))

    assert properties["customer_id"].required is None
    assert all(p.required for name, p in properties.items() if name != "customer_id")


def test_the_sorting_key_becomes_the_primary_key(clickhouse_server, credentials):
    properties = _properties(_import(clickhouse_table=["orders"]))

    assert (properties["order_id"].primaryKey, properties["order_id"].primaryKeyPosition) == (True, 1)
    assert (properties["ordered_at"].primaryKey, properties["ordered_at"].primaryKeyPosition) == (True, 2)
    assert properties["status"].primaryKey is None


def test_comments_become_descriptions(clickhouse_server, credentials):
    odcs = _import(clickhouse_table=["orders"])

    assert odcs.schema_[0].description == "One row per order"
    assert _properties(odcs)["order_id"].description == "The order"


def test_the_server_is_the_one_imported_from(clickhouse_server, credentials):
    server = _import(clickhouse_table=["orders"]).servers[0]

    assert (server.type, server.host, server.port, server.database) == (
        "clickhouse",
        clickhouse.get_container_host_ip(),
        _port(),
        DATABASE,
    )


def test_imported_contract_passes_test_without_editing(clickhouse_server, credentials):
    odcs = _import()

    run = DataContract(data_contract_str=odcs.to_yaml()).test()

    print(run.pretty())
    assert run.result == ResultEnum.passed
    assert all(check.result == ResultEnum.passed for check in run.checks)


def test_import_clickhouse_produces_a_valid_contract(clickhouse_server, credentials):
    run = DataContract(data_contract_str=_import().to_yaml()).lint()

    assert run.result == ResultEnum.passed


def test_import_clickhouse_imports_all_tables_and_views_by_default(clickhouse_server, credentials):
    odcs = _import()

    assert {s.name: s.physicalType for s in odcs.schema_} == {
        "customers": "table",
        "open_orders": "view",
        "orders": "table",
    }


def test_import_clickhouse_fails_on_an_unknown_table(clickhouse_server, credentials):
    with pytest.raises(DataContractException, match="No tables found"):
        _import(clickhouse_table=["no_such_table"])


def test_import_clickhouse_requires_a_database():
    with pytest.raises(DataContractException, match="--database"):
        DataContract.import_from_source("clickhouse", source="localhost")


def test_import_clickhouse_requires_a_host():
    with pytest.raises(DataContractException, match="--source"):
        DataContract.import_from_source("clickhouse", source=None, database=DATABASE)


@pytest.mark.parametrize(
    "type_string, logical_type",
    [
        ("Int8", "integer"),
        ("UInt256", "integer"),
        ("LowCardinality(Nullable(String))", "string"),
        ("FixedString(3)", "string"),
        ("Nullable(Float32)", "number"),
        ("Decimal128(4)", "number"),
        ("Bool", "boolean"),
        ("DateTime('UTC')", "timestamp"),
        ("IPv6", "string"),
        ("Tuple(a String, b Int32)", "object"),
        ("JSON", "object"),
        ("AggregateFunction(uniq, String)", None),
    ],
)
def test_clickhouse_types_map_to_logical_types(type_string, logical_type):
    assert map_clickhouse_type(type_string) == logical_type
