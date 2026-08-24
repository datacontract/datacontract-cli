import ast

import pytest
import yaml
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract
from datacontract.model.exceptions import DataContractException

models_file_path = "fixtures/pydantic-model/models.py"


def properties_of(schema):
    return {prop.name: prop for prop in schema.properties}


def test_cli():
    runner = CliRunner()
    result = runner.invoke(app, ["import", "pydantic-model", "--source", models_file_path])

    assert result.exit_code == 0


def test_import_pydantic_model():
    result = DataContract.import_from_source("pydantic-model", models_file_path)

    with open("fixtures/pydantic-model/expected/models.odcs.yaml") as file:
        expected = file.read()

    assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected)


def test_imported_contract_lints(tmp_path):
    result = DataContract.import_from_source("pydantic-model", models_file_path)
    contract = tmp_path / "datacontract.odcs.yaml"
    contract.write_text(result.to_yaml())

    assert DataContract(data_contract_file=str(contract)).lint().has_passed()


def test_models_used_as_a_field_type_are_nested_not_top_level():
    """Address and LineItem describe columns of Orders, so they are not their own schema."""
    result = DataContract.import_from_source("pydantic-model", models_file_path)

    assert [schema.name for schema in result.schema_] == ["Orders"]
    assert [prop.name for prop in properties_of(result.schema_[0])["shipping_address"].properties] == [
        "street",
        "city",
        "postal_code",
    ]


def test_a_field_is_required_unless_it_is_optional_or_has_a_default():
    result = DataContract.import_from_source("pydantic-model", models_file_path)
    properties = properties_of(result.schema_[0])

    assert properties["order_id"].required is True
    assert properties["note"].required is False  # str | None
    assert properties["is_gift"].required is False  # bool = False
    assert properties["tags"].required is False  # list[str] = []


def test_field_constraints_become_logical_type_options():
    result = DataContract.import_from_source("pydantic-model", models_file_path)
    properties = properties_of(result.schema_[0])

    assert properties["customer_id"].logicalTypeOptions == {"minLength": 1, "maxLength": 64}
    assert properties["order_total"].logicalTypeOptions == {"minimum": 0}
    # Annotated[int, Field(ge=1)], on the item model nested in the array
    quantity = properties_of(properties["line_items"].items)["quantity"]
    assert quantity.logicalTypeOptions == {"minimum": 1}


def test_enums_and_literals_become_a_valid_values_quality_rule():
    result = DataContract.import_from_source("pydantic-model", models_file_path)
    properties = properties_of(result.schema_[0])

    assert properties["status"].quality[0].arguments == {"validValues": ["pending", "shipped", "delivered"]}
    assert properties["channel"].quality[0].arguments == {"validValues": ["web", "mobile", "store"]}
    # A Literal of ints is an integer column, not a string one.
    assert properties["priority"].logicalType == "integer"


def test_descriptions_come_from_the_field_and_the_class_docstring():
    result = DataContract.import_from_source("pydantic-model", models_file_path)
    schema = result.schema_[0]

    assert schema.description == "One row per customer order."
    assert properties_of(properties_of(schema)["line_items"].items)["sku"].description == "Stock keeping unit."


def test_round_trip_through_the_pydantic_exporter_keeps_the_schema(tmp_path):
    """import pydantic-model -> export pydantic-model -> import must not drift."""
    imported = DataContract.import_from_source("pydantic-model", models_file_path)
    contract = tmp_path / "datacontract.odcs.yaml"
    contract.write_text(imported.to_yaml())

    exported = DataContract(data_contract_file=str(contract)).export("pydantic-model")
    generated = tmp_path / "generated_models.py"
    generated.write_text(exported)

    reimported = DataContract.import_from_source("pydantic-model", str(generated))

    # A bytes column is an array in ODCS, and the exporter writes an array without
    # items as list[Any], so those columns are the one thing the trip cannot keep.
    lossy = {prop.name for prop in imported.schema_[0].properties if prop.physicalType == "bytes"}

    def shape(properties):
        return [
            (prop.name, prop.logicalType, shape(prop.properties or []), shape([prop.items] if prop.items else []))
            for prop in properties
            if prop.name not in lossy
        ]

    assert shape(reimported.schema_[0].properties) == shape(imported.schema_[0].properties)


def test_exported_models_are_valid_python(tmp_path):
    """An object property without sub-properties still has to produce a parseable class."""
    imported = DataContract.import_from_source("pydantic-model", models_file_path)
    contract = tmp_path / "datacontract.odcs.yaml"
    contract.write_text(imported.to_yaml())

    exported = DataContract(data_contract_file=str(contract)).export("pydantic-model")

    ast.parse(exported)


def test_a_file_without_models_is_reported(tmp_path):
    source = tmp_path / "no_models.py"
    source.write_text("x = 1\n")

    with pytest.raises(DataContractException) as exception:
        DataContract.import_from_source("pydantic-model", str(source))

    assert "No Pydantic models found" in exception.value.reason


def test_a_file_that_does_not_parse_is_reported(tmp_path):
    source = tmp_path / "broken.py"
    source.write_text("class Broken(BaseModel:\n")

    with pytest.raises(DataContractException) as exception:
        DataContract.import_from_source("pydantic-model", str(source))

    assert "Failed to parse" in exception.value.reason
