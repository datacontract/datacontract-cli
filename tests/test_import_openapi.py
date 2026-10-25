import logging
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract
from datacontract.model.exceptions import DataContractException

ORDERS = "fixtures/import/openapi/orders.yaml"


def import_openapi(source, operation=None):
    return DataContract.import_from_source("openapi", str(source), openapi_operation=operation)


def write_spec(tmp_path: Path, spec: dict) -> Path:
    source = tmp_path / "openapi.yaml"
    source.write_text(yaml.safe_dump({"openapi": "3.1.0", "info": {"title": "API", "version": "1"}, **spec}))
    return source


def get(schema: dict, operation_id: str = None) -> dict:
    operation = {"responses": {"200": {"description": "OK", "content": {"application/json": {"schema": schema}}}}}
    if operation_id:
        operation["operationId"] = operation_id
    return {"get": operation}


def test_cli(tmp_path: Path):
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["import", "openapi", "--source", ORDERS, "--operation", "listOrders", "--output", tmp_path / "dc.yaml"],
    )
    assert result.exit_code == 0

    with open(tmp_path / "dc.yaml") as file:
        actual = yaml.safe_load(file)
    with open("fixtures/import/openapi/orders.odcs.yaml") as file:
        expected = yaml.safe_load(file)
    assert actual == expected


@pytest.mark.parametrize("operation", ["getOrder", "/orders/{orderId}", "GET /orders/{orderId}"])
def test_select_operation_by_id_or_path(operation):
    result = import_openapi(ORDERS, operation)

    (schema,) = result.schema_
    assert schema.name == "getOrder"
    assert schema.description == "One order."
    # a referenced response with a YAML body, the 404 response before it is no success
    assert [p.name for p in schema.properties][:3] == ["order_id", "order_timestamp", "status"]
    # the path parameter becomes a variable that defaults to its example
    assert [s.location for s in result.servers] == [
        "https://eu.api.example.com/v1/orders/${orderId:-ORD-1001}",
        "https://staging.api.example.com/v1/orders/${orderId:-ORD-1001}",
    ]


@pytest.mark.parametrize("operation", ["searchOrders", "POST /orders/search", "post /orders/search"])
def test_post_operation(operation):
    result = import_openapi(ORDERS, operation)

    assert result.schema_[0].name == "searchOrders"
    server = result.servers[0]
    assert server.location == "https://eu.api.example.com/v1/orders/search"
    assert [(p.property, p.value) for p in server.customProperties] == [
        ("method", "POST"),
        ("params", {"limit": "${limit:-100}"}),
        ("body", {"status": "shipped"}),
    ]


def test_bare_path_selects_no_post_operation():
    """A POST operation may change data, so it is only selected by its operationId or method and path."""
    with pytest.raises(DataContractException) as e:
        import_openapi(ORDERS, "/orders/search")

    assert "No GET or POST operation '/orders/search'" in e.value.reason


@pytest.mark.parametrize(
    "media_type, body",
    [
        pytest.param(
            {"example": {"q": "a"}, "examples": {"b": {"value": {"q": "b"}}}, "schema": {"example": {"q": "c"}}},
            {"q": "a"},
            id="media-type-example",
        ),
        pytest.param(
            {"examples": {"b": {"$ref": "#/components/examples/B"}}, "schema": {"example": {"q": "c"}}},
            {"q": "b"},
            id="first-named-example",
        ),
        pytest.param({"schema": {"$ref": "#/components/schemas/Query"}}, {"q": "c"}, id="schema-example"),
    ],
)
def test_post_body_from_request_body_example(tmp_path: Path, media_type, body):
    operation = get({"type": "object", "properties": {"id": {"type": "integer"}}})["get"]
    operation["requestBody"] = {"content": {"application/json": media_type}}
    source = write_spec(
        tmp_path,
        {
            "servers": [{"url": "https://api.example.com"}],
            "paths": {"/search": {"post": operation}},
            "components": {
                "examples": {"B": {"value": {"q": "b"}}},
                "schemas": {"Query": {"type": "object", "example": {"q": "c"}}},
            },
        },
    )

    result = import_openapi(source, "POST /search")

    assert {p.property: p.value for p in result.servers[0].customProperties}["body"] == body


def test_post_without_body_example_warns(tmp_path: Path, caplog):
    operation = get({"type": "object", "properties": {"id": {"type": "integer"}}})["get"]
    operation["requestBody"] = {"required": True, "content": {"application/json": {"schema": {"type": "object"}}}}
    source = write_spec(
        tmp_path, {"servers": [{"url": "https://api.example.com"}], "paths": {"/search": {"post": operation}}}
    )

    with caplog.at_level(logging.WARNING):
        result = import_openapi(source, "POST /search")

    assert [p.property for p in result.servers[0].customProperties] == ["method"]
    assert "The request body of POST /search has no JSON example" in caplog.text


def test_skips_relative_server(caplog):
    with caplog.at_level(logging.WARNING):
        import_openapi(ORDERS, "listOrders")

    assert "Skipped the server '/v1'" in caplog.text


def test_single_get_operation_needs_no_selection(tmp_path: Path):
    source = write_spec(
        tmp_path,
        {
            "servers": [{"url": "https://api.example.com"}],
            "paths": {"/customers/{id}/orders": get({"type": "object", "properties": {"id": {"type": "integer"}}})},
        },
    )

    result = import_openapi(source)

    (schema,) = result.schema_
    # without an operationId, the name comes from the path
    assert schema.name == "customers_id_orders"
    assert schema.properties[0].logicalType == "integer"
    # a path parameter without an example or default is a variable to set
    assert result.servers[0].server == "api.example.com"
    assert result.servers[0].location == "https://api.example.com/customers/${id}/orders"


def test_nullable_properties_are_not_required(tmp_path: Path):
    """ODCS `required` means not null, so a property that admits null is optional."""
    schema = {
        "type": "object",
        "required": ["nullable_3_0", "nullable_3_1", "id"],
        "properties": {
            "nullable_3_0": {"type": "string", "nullable": True},
            "nullable_3_1": {"type": ["integer", "null"]},
            "id": {"type": "string"},
        },
    }
    source = write_spec(tmp_path, {"paths": {"/things": get(schema)}})

    result = import_openapi(source)

    props = {p.name: p for p in result.schema_[0].properties}
    assert {name: p.required for name, p in props.items()} == {"nullable_3_0": None, "nullable_3_1": None, "id": True}
    assert (props["nullable_3_0"].logicalType, props["nullable_3_1"].logicalType) == ("string", "integer")


def test_several_get_operations_need_a_selection():
    with pytest.raises(DataContractException) as e:
        import_openapi(ORDERS)

    assert (
        "listOrders (GET /orders), createOrder (POST /orders), searchOrders (POST /orders/search), "
        "getOrder (GET /orders/{orderId}), GET /health" in e.value.reason
    )


def test_unknown_operation():
    with pytest.raises(DataContractException) as e:
        import_openapi(ORDERS, "deleteOrder")

    assert "No GET or POST operation 'deleteOrder'" in e.value.reason


def test_operation_without_json_or_yaml_response():
    with pytest.raises(DataContractException) as e:
        import_openapi(ORDERS, "/health")

    assert "no success response with a JSON or YAML schema" in e.value.reason


def test_swagger_2_is_rejected(tmp_path: Path):
    source = tmp_path / "swagger.yaml"
    source.write_text("swagger: '2.0'\ninfo: {title: API, version: '1'}\npaths: {}\n")

    with pytest.raises(DataContractException) as e:
        import_openapi(source)

    assert "is not an OpenAPI 3.x document" in e.value.reason


SHOP = "fixtures/import/openapi/shop.yaml"


def test_several_operations_name_their_endpoints():
    result = import_openapi(SHOP, ["listCustomers", "listOrders", "POST /orders/search", "GET /customers"])

    assert [schema.name for schema in result.schema_] == ["listCustomers", "listOrders", "searchOrders"]
    # the server is located at the base URL, and each schema at its endpoint below it
    (server,) = result.servers
    assert server.location == "https://api.example.com/v1"
    assert server.customProperties is None
    assert [[(p.property, p.value) for p in schema.customProperties] for schema in result.schema_] == [
        [("endpoint", "/customers")],
        [("endpoint", "/orders"), ("params", {"status": "${status:-open}"})],
        [("endpoint", "/orders/search"), ("method", "POST"), ("body", {"status": "shipped"})],
    ]


def test_cli_asks_for_operations_in_a_terminal(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("datacontract.command_import._interactive", lambda: True)

    result = CliRunner().invoke(
        app,
        ["import", "openapi", "--source", SHOP, "--output", tmp_path / "dc.yaml"],
        input="7\nx\n1-2\n",
    )

    assert result.exit_code == 0, result.output
    # createOrder has no response to import, so it is not offered
    assert "createOrder" not in result.output
    assert "3. searchOrders (POST /orders/search)  (POST: import it only if it reads data)" in result.output
    assert result.output.count("Enter numbers between 1 and 3") == 2
    contract = yaml.safe_load((tmp_path / "dc.yaml").read_text())
    assert [schema["name"] for schema in contract["schema"]] == ["listCustomers", "listOrders"]


def test_cli_takes_several_operations(tmp_path: Path):
    result = CliRunner().invoke(
        app,
        ["import", "openapi", "--source", SHOP, "--operation", "listCustomers", "--operation", "listOrders"],
    )

    assert result.exit_code == 0, result.output
    contract = yaml.safe_load(result.stdout)
    assert [schema["name"] for schema in contract["schema"]] == ["listCustomers", "listOrders"]
