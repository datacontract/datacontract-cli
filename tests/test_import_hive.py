"""Tests for the Hive importer, run against a real HiveServer2 container."""

import pytest

from datacontract.data_contract import DataContract
from datacontract.model.exceptions import DataContractException
from datacontract.model.run import ResultEnum
from tests.test_test_hive import HiveContainer

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

hive = HiveContainer()


@pytest.fixture(scope="module")
def hive_server(request):
    hive.start()
    request.addfinalizer(hive.stop)
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
        "tags": ("array<string>", "array"),
        "shipping": ("struct<city:string,zip:string>", "object"),
        "attributes": ("map<string,bigint>", "map"),
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
