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

    assert "listOrders (GET /orders), getOrder (GET /orders/{orderId}), /health" in e.value.reason


def test_unknown_operation():
    with pytest.raises(DataContractException) as e:
        import_openapi(ORDERS, "createOrder")

    assert "No GET operation 'createOrder'" in e.value.reason


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
