import json
import logging
import os
from pathlib import Path

import yaml
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract

# logging.basicConfig(level=logging.DEBUG, force=True)


def test_cli():
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "import",
            "jsonschema",
            "--source",
            "fixtures/import/orders.json",
        ],
    )
    assert result.exit_code == 0


def test_cli_with_output(tmp_path: Path):
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "import",
            "jsonschema",
            "--source",
            "fixtures/import/orders_union-types.json",
            "--output",
            tmp_path / "datacontract.yaml",
        ],
    )
    assert result.exit_code == 0
    assert os.path.exists(tmp_path / "datacontract.yaml")

    with open(tmp_path / "datacontract.yaml") as file:
        actual = file.read()
    with open("fixtures/import/orders_union-types_datacontract.yml") as file:
        expected = file.read()

    assert yaml.safe_load(actual) == yaml.safe_load(expected)


def test_import_json_schema_orders():
    result = DataContract.import_from_source("jsonschema", "fixtures/import/orders_union-types.json")

    with open("fixtures/import/orders_union-types_datacontract.yml") as file:
        expected = file.read()

    print("Result:\n", result.to_yaml())
    assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected)


def test_import_json_schema_football():
    result = DataContract.import_from_source("jsonschema", "fixtures/import/football.json")

    with open("fixtures/import/football-datacontract.yml") as file:
        expected = file.read()

    print("Result:\n", result.to_yaml())
    assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected)


def test_import_json_schema_football_deeply_nested_no_required():
    result = DataContract.import_from_source("jsonschema", "fixtures/import/football_deeply_nested_no_required.json")

    with open("fixtures/import/football_deeply_nested_no_required_datacontract.yml") as file:
        expected = file.read()

    print("Result:\n", result.to_yaml())
    assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected)


def _import_properties(tmp_path: Path, properties: dict) -> dict:
    source = tmp_path / "schema.json"
    source.write_text(json.dumps({"title": "orders", "type": "object", "properties": properties}))
    result = DataContract.import_from_source("jsonschema", str(source))
    return {p.name: p for p in result.schema_[0].properties}


def test_import_json_schema_nullable_any_of_keeps_the_type(tmp_path: Path):
    properties = _import_properties(
        tmp_path,
        {
            "total": {"anyOf": [{"type": "integer"}, {"type": "null"}], "title": "Total"},
            "customer": {
                "oneOf": [{"type": "null"}, {"type": "object", "properties": {"email": {"type": "string"}}}],
            },
        },
    )

    assert properties["total"].logicalType == "integer"
    assert properties["total"].businessName == "Total"
    assert properties["customer"].logicalType == "object"
    assert [p.name for p in properties["customer"].properties] == ["email"]


def test_import_json_schema_unions_warn_and_import_as_string(tmp_path: Path, caplog):
    with caplog.at_level(logging.WARNING):
        properties = _import_properties(
            tmp_path,
            {
                "id": {"type": ["string", "integer", "null"]},
                "flag": {"anyOf": [{"type": "integer"}, {"type": "boolean"}]},
                "ref": {"oneOf": [{"type": "string"}, {"$ref": "#/$defs/Address"}]},
            },
        )

    assert {name: (p.logicalType, p.physicalType) for name, p in properties.items()} == {
        "id": ("string", "string|integer"),
        "flag": ("string", "integer|boolean"),
        "ref": ("string", "string|Address"),
    }
    assert "id (string|integer), flag (integer|boolean), ref (string|Address)" in caplog.text
