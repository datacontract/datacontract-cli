import json
import logging
import os
from pathlib import Path

import pytest
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
                "shipping": {
                    "anyOf": [
                        {"type": "object", "properties": {"street": {"type": "string"}}},
                        {"type": "object", "properties": {"locker": {"type": "integer"}}},
                    ]
                },
                "code": {"anyOf": [{"type": "integer"}, {"const": "n/a"}]},
                "status": {"anyOf": [{"const": "open"}, {"const": "closed"}]},
            },
        )

    assert {name: (p.logicalType, p.physicalType) for name, p in properties.items()} == {
        "id": ("string", "string|integer"),
        "flag": ("string", "integer|boolean"),
        "ref": ("string", "string|Address"),
        "shipping": ("string", "object|object"),
        "code": ("string", "integer|string"),
        "status": ("string", "string"),
    }
    assert (
        "ODCS has no union type, so these properties are imported as string: id (string|integer), "
        "flag (integer|boolean), ref (string|Address), shipping (object|object), code (integer|string)"
    ) in caplog.text


def test_import_json_schema_boolean_branches(tmp_path: Path):
    properties = _import_properties(
        tmp_path,
        {
            "anything": {"anyOf": [True, {"type": "integer"}]},
            "total": {"anyOf": [False, {"type": "integer"}]},
        },
    )

    # true admits every value, so the property is untyped; false admits none, so it is dropped
    assert (properties["anything"].logicalType, properties["anything"].physicalType) == ("string", "string")
    assert properties["total"].logicalType == "integer"


def test_import_boolean_schemas(tmp_path):
    source = tmp_path / "schema.json"
    source.write_text(
        json.dumps({"properties": {"anything": True, "never": False, "list": {"type": "array", "items": True}}})
    )

    result = DataContract.import_from_source("jsonschema", str(source))

    properties = {p.name: p for p in result.schema_[0].properties}
    assert list(properties) == ["anything", "list"]
    assert properties["list"].items is not None


def test_import_an_infinite_bound_as_no_bound(tmp_path):
    source = tmp_path / "schema.json"
    source.write_text(
        '{"properties": {"n": {"type": "number", "minimum": 0, "maximum": 1e400, "exclusiveMinimum": -1e400}}}'
    )

    result = DataContract.import_from_source("jsonschema", str(source))

    assert result.schema_[0].properties[0].logicalTypeOptions == {"minimum": 0}


def _import(tmp_path: Path, schema: dict):
    source = tmp_path / "schema.json"
    source.write_text(json.dumps(schema))
    return DataContract.import_from_source("jsonschema", str(source))


ADDRESS = {
    "type": "object",
    "properties": {"city": {"type": "string"}, "zip": {"type": "string", "pattern": "^[0-9]{5}$"}},
    "required": ["city"],
}


@pytest.mark.parametrize("definitions", ["$defs", "definitions"])
def test_import_resolves_local_refs(tmp_path: Path, definitions):
    result = _import(
        tmp_path,
        {
            "title": "customer",
            "properties": {
                "home": {"$ref": f"#/{definitions}/Address", "description": "Where they live"},
                "addresses": {"type": "array", "items": {"$ref": f"#/{definitions}/Address"}},
                "id": {"$ref": f"#/{definitions}/Id"},
            },
            definitions: {"Address": ADDRESS, "Id": {"type": "integer", "minimum": 1}},
        },
    )

    props = {p.name: p for p in result.schema_[0].properties}
    home = props["home"]
    assert (home.logicalType, home.description) == ("object", "Where they live")  # keywords next to $ref apply
    assert [(p.name, p.required) for p in home.properties] == [("city", True), ("zip", None)]
    assert [p.name for p in props["addresses"].items.properties] == ["city", "zip"]
    assert (props["id"].logicalType, props["id"].logicalTypeOptions) == ("integer", {"minimum": 1})


def test_import_resolves_a_ref_at_the_root(tmp_path: Path):
    result = _import(tmp_path, {"title": "address", "$ref": "#/$defs/Address", "$defs": {"Address": ADDRESS}})

    assert [p.name for p in result.schema_[0].properties] == ["city", "zip"]


def test_import_stops_a_recursive_ref_at_its_repetition(tmp_path: Path, caplog):
    with caplog.at_level(logging.WARNING):
        result = _import(
            tmp_path,
            {
                "properties": {"tree": {"$ref": "#/$defs/Node"}},
                "$defs": {
                    "Node": {
                        "type": "object",
                        "properties": {
                            "label": {"type": "string"},
                            "children": {"type": "array", "items": {"$ref": "#/$defs/Node"}},
                        },
                    }
                },
            },
        )

    tree = result.schema_[0].properties[0]
    children = {p.name: p for p in tree.properties}["children"]
    assert children.items.logicalType == "object" and children.items.properties is None
    assert "contain themselves" in caplog.text and "#/$defs/Node" in caplog.text


def test_import_warns_about_refs_it_cannot_resolve(tmp_path: Path, caplog):
    with caplog.at_level(logging.WARNING):
        result = _import(
            tmp_path,
            {"properties": {"remote": {"$ref": "https://example.com/address.json"}, "gone": {"$ref": "#/$defs/Gone"}}},
        )

    assert [p.logicalType for p in result.schema_[0].properties] == ["string", "string"]
    assert "https://example.com/address.json" in caplog.text and "#/$defs/Gone" in caplog.text


def test_import_merges_all_of(tmp_path: Path):
    result = _import(
        tmp_path,
        {
            "title": "customer",
            "allOf": [
                {"$ref": "#/$defs/Base"},
                {"properties": {"name": {"type": "string"}, "id": {"type": "string"}}, "required": ["name"]},
            ],
            "properties": {
                "score": {"allOf": [{"type": "integer"}, {"minimum": 5}]},
                "address": {"allOf": [{"$ref": "#/$defs/Address"}, {"properties": {"country": {"type": "string"}}}]},
            },
            "$defs": {
                "Base": {"type": "object", "properties": {"id": {"type": "integer"}}, "required": ["id"]},
                "Address": ADDRESS,
            },
        },
    )

    props = {p.name: p for p in result.schema_[0].properties}
    # the schema's own properties, then those of its branches in order; the first definition of a name wins
    assert [(p.name, p.logicalType, p.required) for p in result.schema_[0].properties] == [
        ("score", "integer", None),
        ("address", "object", None),
        ("id", "integer", True),
        ("name", "string", True),
    ]
    assert props["score"].logicalTypeOptions == {"minimum": 5}
    assert [p.name for p in props["address"].properties] == ["city", "zip", "country"]


def test_import_const_as_the_only_value(tmp_path: Path):
    properties = _import_properties(tmp_path, {"version": {"type": "string", "const": "v1"}, "kind": {"const": 42}})

    assert [e.value for e in properties["version"].enum] == ["v1"]
    assert (properties["kind"].logicalType, [e.value for e in properties["kind"].enum]) == ("integer", [42])


def test_import_array_and_number_options(tmp_path: Path):
    properties = _import_properties(
        tmp_path,
        {
            "tags": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 3, "uniqueItems": True},
            "step": {"type": "number", "multipleOf": 0.5, "examples": [1.5, 2]},
        },
    )

    assert properties["tags"].logicalTypeOptions == {"minItems": 1, "maxItems": 3, "uniqueItems": True}
    assert properties["step"].logicalTypeOptions == {"multipleOf": 0.5}
    assert properties["step"].examples == [1.5, 2]


def test_import_additional_properties_as_a_map(tmp_path: Path):
    properties = _import_properties(
        tmp_path, {"labels": {"type": "object", "additionalProperties": {"type": "integer", "minimum": 0}}}
    )

    labels = properties["labels"]
    assert labels.logicalType == "map"
    assert (labels.map.value.logicalType, labels.map.value.logicalTypeOptions) == ("integer", {"minimum": 0})


def test_import_warns_about_keywords_odcs_cannot_express(tmp_path: Path, caplog):
    with caplog.at_level(logging.WARNING):
        _import(
            tmp_path,
            {
                "properties": {
                    "meta": {
                        "type": "object",
                        "properties": {"a": {"type": "string"}},
                        "additionalProperties": {"type": "string"},
                        "patternProperties": {"^x": {}},
                    },
                    "cond": {"type": "string", "not": {"const": "x"}, "if": {"minLength": 2}, "then": {"maxLength": 4}},
                },
                "dependentRequired": {"a": ["b"]},
            },
        )

    assert (
        "ODCS cannot express these keywords, which are not imported: dependentRequired (root), "
        "patternProperties (meta), additionalProperties (meta), if (cond), not (cond)"
    ) in caplog.text
