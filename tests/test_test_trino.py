import logging
import time

import pytest
from testcontainers.core.container import DockerContainer
from trino.dbapi import connect

from datacontract.data_contract import DataContract
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
