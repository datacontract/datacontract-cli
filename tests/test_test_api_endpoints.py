"""`datacontract test` against an API server whose schemas are served by different endpoints."""

import json

import pytest
import yaml
from open_data_contract_standard.model import Relationship

from datacontract.data_contract import DataContract

CONTRACT = """\
apiVersion: v3.1.0
kind: DataContract
id: shop
version: 1.0.0
status: active
servers:
  - server: production
    type: api
    location: {url}/v1
schema:
  - name: customers
    customProperties:
      - property: endpoint
        value: /customers
    properties:
      - name: id
        logicalType: string
        required: true
        unique: true
      - name: email
        logicalType: string
  - name: orders
    customProperties:
      - property: endpoint
        value: orders
      - property: params
        value:
          status: ${{status:-open}}
    properties:
      - name: order_id
        logicalType: string
        required: true
      - name: customer_id
        logicalType: string
        relationships:
          - to: customers.id
      - name: amount
        logicalType: number
"""

CUSTOMERS = [{"id": "C-1", "email": "jane@example.com"}, {"id": "C-2", "email": "john@example.com"}]
ORDERS = [
    {"order_id": "O-1", "customer_id": "C-1", "amount": 12.5},
    {"order_id": "O-2", "customer_id": "C-2", "amount": 7},
    {"order_id": "O-3", "customer_id": None, "amount": 3},
]
RELATIONSHIP = "orders__customer_id__customers__id__field_relationships"


def odcs(api) -> dict:
    return yaml.safe_load(CONTRACT.format(url=api.url))


def contract(api, schema_name="all") -> DataContract:
    return DataContract(data_contract_str=yaml.safe_dump(odcs(api)), schema_name=schema_name)


def serve(api, customers=CUSTOMERS, orders=ORDERS):
    api.bodies = {"/v1/customers": json.dumps(customers), "/v1/orders": json.dumps(orders)}


def checks(run) -> dict:
    return {(check.key or check.name, check.model): check.result for check in run.checks}


def failed(run) -> list:
    return [key for key, result in checks(run).items() if result == "failed"]


def test_each_schema_is_fetched_from_its_endpoint(api):
    serve(api)

    run = contract(api).test()

    assert run.result == "passed", run.pretty()
    assert sorted(api.paths) == ["/v1/customers", "/v1/orders?status=open"]
    assert checks(run)[(RELATIONSHIP, "orders")] == "passed"
    assert checks(run)[("customers__id__field_unique", "customers")] == "passed"


def test_foreign_key_missing_from_the_other_endpoint(api):
    serve(api, orders=[*ORDERS, {"order_id": "O-4", "customer_id": "C-9", "amount": 1}])

    run = contract(api).test()

    assert run.result == "failed"
    assert failed(run) == [(RELATIONSHIP, "orders")]


def test_each_response_is_validated_against_its_own_schema(api):
    serve(api, customers=[*CUSTOMERS, {"email": "no-id@example.com"}])

    run = contract(api).test()

    assert run.result == "failed"
    assert checks(run)[("Check that JSON has valid schema", "orders")] == "passed"
    assert sorted(failed(run)) == [
        ("Check that JSON has valid schema", "customers"),
        ("customers__id__field_required", "customers"),
    ]


def test_schema_name_fetches_only_its_endpoint(api):
    serve(api)

    run = contract(api, schema_name="orders").test()

    assert api.paths == ["/v1/orders?status=open"]
    # the referenced schema is not read, so the relationship is not checked
    assert checks(run)[(RELATIONSHIP, "orders")] == "warning"


def test_post_endpoint(api):
    serve(api)
    api.bodies["/v1/customers/search"] = json.dumps(CUSTOMERS)
    data_contract = odcs(api)
    data_contract["schema"][0]["customProperties"] = [
        {"property": "endpoint", "value": "/customers/search"},
        {"property": "method", "value": "POST"},
        {"property": "body", "value": {"active": True}},
    ]

    run = DataContract(data_contract_str=yaml.safe_dump(data_contract)).test()

    assert run.result == "passed", run.pretty()
    assert api.methods == ["POST", "GET"]
    assert json.loads(api.request_bodies[0]) == {"active": True}


@pytest.mark.parametrize(
    "server_properties, customers_properties, reason",
    [
        ([], [], "Schema 'customers' needs an endpoint custom property"),
        ([], [{"property": "endpoint", "value": {"path": "/c"}}], "Schema 'customers' needs an endpoint"),
        (
            [],
            [{"property": "endpoint", "value": "/c"}, {"property": "body", "value": {}}],
            "A body requires method POST",
        ),
        (
            [{"property": "method", "value": "POST"}],
            [{"property": "endpoint", "value": "/c"}],
            "The method custom property of the server cannot be combined with schema endpoints",
        ),
    ],
)
def test_invalid_endpoints(api, server_properties, customers_properties, reason):
    data_contract = odcs(api)
    data_contract["servers"][0]["customProperties"] = server_properties
    data_contract["schema"][0]["customProperties"] = customers_properties

    run = DataContract(data_contract_str=yaml.safe_dump(data_contract)).test()

    assert run.result in ("failed", "error")
    assert reason in run.pretty()
    assert api.paths == []


def test_request_properties_of_a_schema_require_an_endpoint(api):
    data_contract = odcs(api)
    del data_contract["schema"][0]["customProperties"]
    data_contract["schema"][1]["customProperties"] = [{"property": "params", "value": {"status": "open"}}]

    run = DataContract(data_contract_str=yaml.safe_dump(data_contract)).test()

    assert run.result in ("failed", "error")
    assert "Schema 'orders' has the params custom property, which requires an endpoint" in run.pretty()
    assert api.paths == []


def test_schema_name_that_is_no_file_name(api):
    data_contract = odcs(api)
    data_contract["schema"][0]["name"] = "../customers"
    del data_contract["schema"][1]["properties"][1]["relationships"]

    run = DataContract(data_contract_str=yaml.safe_dump(data_contract)).test()

    assert run.result in ("failed", "error")
    assert "its name is no file name" in run.pretty()
    assert api.paths == []


def test_imported_operations_with_a_relationship(api):
    data_contract = DataContract.import_from_source(
        "openapi", "fixtures/import/openapi/shop.yaml", openapi_operation=["listCustomers", "listOrders"]
    )
    data_contract.servers[0].location = f"{api.url}/v1"
    orders = next(schema for schema in data_contract.schema_ if schema.name == "listOrders")
    customer_id = next(prop for prop in orders.properties if prop.name == "customer_id")
    customer_id.relationships = [Relationship(to="listCustomers.id")]
    serve(api, orders=[*ORDERS, {"order_id": "O-4", "customer_id": "C-9", "amount": 1}])

    run = DataContract(data_contract=data_contract).test()

    assert run.result == "failed"
    assert sorted(api.paths) == ["/v1/customers", "/v1/orders?status=open"]
    assert failed(run) == [("listOrders__customer_id__listCustomers__id__field_relationships", "listOrders")]
