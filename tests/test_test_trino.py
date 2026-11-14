import logging
import time

import pytest
import trino as trino_client
from testcontainers.core.container import DockerContainer
from trino.dbapi import connect

from datacontract.data_contract import DataContract
from datacontract.model.exceptions import DataContractException
from datacontract.model.run import ResultEnum
from tests.dcs_deprecation import assert_dcs_deprecation_is_the_only_warning, without_dcs_deprecation

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

    assert_dcs_deprecation_is_the_only_warning(run)
    assert all(check.result == "passed" for check in without_dcs_deprecation(run))


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
    data_contract_str = data_contract_str.replace("__PORT__", str(port))
    return data_contract_str


NESTED_CONTRACT = """apiVersion: v3.1.0
kind: DataContract
id: trino-nested
version: 1.0.0
status: active
servers:
  - server: trino
    type: trino
    host: localhost
    port: __PORT__
    catalog: memory
    schema: my_schema
schema:
  - name: orders
    properties:
      - name: order_id
        logicalType: integer
        required: true
      - name: items
        logicalType: array
        items:
          logicalType: object
          properties:
            - name: sku
              logicalType: string
              required: true
              unique: true
      - name: tags
        logicalType: array
        items:
          logicalType: string
          quality:
            - metric: invalidValues
              arguments:
                validValues: [new, vip]
              mustBe: 0
      - name: customer
        logicalType: object
        properties:
          - name: email
            logicalType: string
            required: true
            quality:
              - type: sql
                query: SELECT COUNT(*) FROM {model} WHERE {property} NOT LIKE '%@%'
                mustBe: 0
"""

ITEM = "row(sku varchar, qty integer)"
CUSTOMER = "row(id bigint, email varchar)"


def test_nested_rules_fail_on_the_parent_rows_that_violate_them(trino_container, monkeypatch):
    conn = connect(host="localhost", port=trino.get_exposed_port(8080), user="my_user", catalog="memory")
    cursor = conn.cursor()
    cursor.execute("CREATE SCHEMA IF NOT EXISTS my_schema")
    cursor.execute(
        f"CREATE TABLE my_schema.orders (order_id bigint, items array({ITEM}), tags array(varchar), customer {CUSTOMER})"
    )
    # order 2 has an item without a sku, order 3 repeats a sku, a disallowed tag and no email;
    # orders 4 and 5 have no items at all
    cursor.execute(f"""INSERT INTO my_schema.orders VALUES
        (1, ARRAY[CAST(ROW('A', 1) AS {ITEM}), CAST(ROW('B', 2) AS {ITEM})], ARRAY['new'],
            CAST(ROW(1, 'a@example.com') AS {CUSTOMER})),
        (2, ARRAY[CAST(ROW(NULL, 1) AS {ITEM})], ARRAY['vip'], CAST(ROW(2, 'b@example.com') AS {CUSTOMER})),
        (3, ARRAY[CAST(ROW('C', 1) AS {ITEM}), CAST(ROW('C', 3) AS {ITEM})], ARRAY['bogus'],
            CAST(ROW(3, NULL) AS {CUSTOMER})),
        (4, CAST(ARRAY[] AS array({ITEM})), ARRAY['new'], CAST(ROW(4, 'd@example.com') AS {CUSTOMER})),
        (5, NULL, NULL, CAST(ROW(5, 'e@example.com') AS {CUSTOMER}))""")
    monkeypatch.setenv("DATACONTRACT_TRINO_USERNAME", "my_user")
    monkeypatch.setenv("DATACONTRACT_TRINO_PASSWORD", "")

    contract = NESTED_CONTRACT.replace("__PORT__", str(trino.get_exposed_port(8080)))
    run = DataContract(data_contract_str=contract).test()

    print(run.pretty())
    failed = [c for c in run.checks if c.result != ResultEnum.passed]
    assert {(c.field, c.type) for c in failed} == {
        ("items[].sku", "field_required"),
        ("items[].sku", "field_unique"),
        ("tags[]", "field_invalid_values"),
        ("customer.email", "field_required"),
    }
    assert all(c.result == ResultEnum.failed and c.diagnostics["value"] == 1 for c in failed)


TYPED_CONTRACT = """apiVersion: v3.1.0
kind: DataContract
id: trino-nested-types
version: 1.0.0
status: active
servers:
  - server: trino
    type: trino
    host: localhost
    port: __PORT__
    catalog: memory
    schema: my_schema
schema:
  - name: shipments
    properties:
      - name: items
        physicalType: array
        logicalType: array
        items:
          physicalType: row
          logicalType: object
          properties:
            - name: sku
              physicalType: varchar(10)
            - name: qty
              physicalType: integer
      - name: carrier
        physicalType: row(name varchar, code varchar(3))
        logicalType: object
"""


def test_nested_physical_types_are_checked_on_their_own_lines(trino_container, monkeypatch):
    conn = connect(host="localhost", port=trino.get_exposed_port(8080), user="my_user", catalog="memory")
    cursor = conn.cursor()
    cursor.execute("CREATE SCHEMA IF NOT EXISTS my_schema")
    cursor.execute(
        "CREATE TABLE my_schema.shipments "
        "(items array(row(sku varchar(20), qty integer)), carrier row(name varchar, code varchar(3)))"
    )
    monkeypatch.setenv("DATACONTRACT_TRINO_USERNAME", "my_user")
    monkeypatch.setenv("DATACONTRACT_TRINO_PASSWORD", "")

    contract = TYPED_CONTRACT.replace("__PORT__", str(trino.get_exposed_port(8080)))
    run = DataContract(data_contract_str=contract).test()

    print(run.pretty())
    failed = [c for c in run.checks if c.result != ResultEnum.passed]
    assert [(c.field, c.type, c.result) for c in failed] == [("items[].sku", "field_physical_type", ResultEnum.failed)]
    assert failed[0].reason == "expected physical type 'varchar(10)' but the column is 'varchar(20)'"
    assert {(c.field, c.type) for c in run.checks if c.type == "field_physical_type"} == {
        ("items", "field_physical_type"),
        ("items[]", "field_physical_type"),
        ("items[].sku", "field_physical_type"),
        ("items[].qty", "field_physical_type"),
        ("carrier", "field_physical_type"),
    }


TRINO_PORT = 8080
CATALOG = "memory"
SCHEMA = "shop"

SEED = [
    f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SCHEMA}",
    f"""CREATE TABLE IF NOT EXISTS {CATALOG}.{SCHEMA}.orders (
          order_id varchar(36), order_total decimal(10,2), line_count integer,
          ordered_at timestamp(3), tags array(varchar), notes varchar)""",
    f"INSERT INTO {CATALOG}.{SCHEMA}.orders VALUES ('CX-263-DU', 50.00, 2, current_timestamp(3), ARRAY['a'], 'hi')",
    f"CREATE TABLE IF NOT EXISTS {CATALOG}.{SCHEMA}.customers (id integer)",
]


@pytest.fixture(scope="module")
def trino_server():
    _seed()


@pytest.fixture
def credentials(monkeypatch):
    monkeypatch.setenv("DATACONTRACT_TRINO_USERNAME", "my_user")
    monkeypatch.setenv("DATACONTRACT_TRINO_PASSWORD", "")


def _port():
    return int(trino.get_exposed_port(TRINO_PORT))


def _seed():
    connection = trino_client.dbapi.connect(
        host=trino.get_container_host_ip(), port=_port(), user="my_user", catalog=CATALOG
    )
    cursor = connection.cursor()
    for statement in SEED:
        cursor.execute(statement)
        cursor.fetchall()
    connection.close()


def _import(**kwargs):
    kwargs.setdefault("catalog", CATALOG)
    kwargs.setdefault("schema", SCHEMA)
    kwargs.setdefault("port", _port())
    return DataContract.import_from_source("trino", trino.get_container_host_ip(), **kwargs)


def test_import_trino_takes_the_declared_type_verbatim(trino_server, credentials):
    result = _import(trino_table=["orders"])
    types = {prop.name: prop.physicalType for prop in result.schema_[0].properties}

    assert types == {
        "order_id": "varchar(36)",
        "order_total": "decimal(10,2)",
        "line_count": "integer",
        "ordered_at": "timestamp(3)",
        "tags": "array(varchar)",
        "notes": "varchar",
    }


def test_imported_contract_passes_test_without_editing(trino_server, credentials):
    """The point of the native import: import, then test, no hand-editing."""
    result = _import(trino_table=["orders"])

    run = DataContract(data_contract_str=result.to_yaml()).test()

    print(run.pretty())
    assert run.result == ResultEnum.passed


def test_a_wrong_physical_type_is_caught(trino_server, credentials):
    """Trino's information_schema has no length columns, so asking for them used
    to fail the whole query and skip this check silently."""
    result = _import(trino_table=["orders"])
    result.schema_[0].properties[0].physicalType = "integer"

    run = DataContract(data_contract_str=result.to_yaml()).test()

    assert run.result == ResultEnum.failed
    assert any("varchar(36)" in (check.reason or "") for check in run.checks)


def test_import_trino_produces_a_valid_contract(trino_server, credentials):
    result = _import()

    assert DataContract(data_contract_str=result.to_yaml()).lint().result == ResultEnum.passed


def test_import_trino_imports_all_tables_by_default(trino_server, credentials):
    result = _import()

    assert [schema.name for schema in result.schema_] == ["customers", "orders"]


def test_import_trino_fails_on_an_unknown_table(trino_server, credentials):
    with pytest.raises(DataContractException) as exc_info:
        _import(trino_table=["does_not_exist"])

    assert "No tables found" in exc_info.value.reason


def test_import_trino_requires_a_catalog():
    with pytest.raises(DataContractException) as exc_info:
        DataContract.import_from_source("trino", "localhost", schema="s")

    assert "catalog is required" in exc_info.value.reason


def test_import_trino_requires_a_schema():
    with pytest.raises(DataContractException) as exc_info:
        DataContract.import_from_source("trino", "localhost", catalog="c")

    assert "schema is required" in exc_info.value.reason


def test_import_trino_requires_a_host():
    with pytest.raises(DataContractException) as exc_info:
        DataContract.import_from_source("trino", None, catalog="c", schema="s")

    assert "host is required" in exc_info.value.reason
