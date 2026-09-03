"""Round trip every example contract through the Pydantic exporter and importer.

`datacontract export pydantic-model` and `datacontract import pydantic-model` are
each other's inverse, so a contract exported to Pydantic models and imported back
has to describe the same schema. The example contracts under `examples/` are the
corpus: they are produced by ten different importers, so they cover far more
column shapes than a hand-written fixture would.

What a Python annotation cannot carry does not survive, and is not asserted here:
`physicalType` is database specific, and constraints, quality rules and examples
have no place in a bare annotation. Name, logical type, requiredness, description
and nesting do survive, and that is what a round trip has to preserve.
"""

import ast
from pathlib import Path

import pytest

from datacontract.data_contract import DataContract
from datacontract.lint import resolve


def _names_are_python_identifiers(contract_file: Path) -> bool:
    """Whether every schema and property name can become a Python class or field name."""

    def properties_ok(properties) -> bool:
        return all(
            prop.name.isidentifier()
            and properties_ok(prop.properties or [])
            and properties_ok([prop.items] if prop.items else [])
            for prop in properties or []
        )

    contract = resolve.resolve_data_contract(data_contract_location=str(contract_file))
    return all(schema.name.isidentifier() and properties_ok(schema.properties) for schema in contract.schema_ or [])


EXAMPLES = [
    pytest.param(
        path,
        id=path.parent.name,
        marks=[]
        if _names_are_python_identifiers(path)
        else pytest.mark.xfail(
            reason="the Pydantic exporter does not map names that are not Python identifiers", strict=True
        ),
    )
    for path in sorted((Path(__file__).resolve().parents[1] / "examples").rglob("*.odcs.yaml"))
]


def shape(properties):
    """The part of a property the Pydantic representation is able to carry."""
    return [
        (
            prop.name,
            prop.logicalType,
            bool(prop.required),
            prop.description,
            shape(prop.properties or []),
            shape([prop.items] if prop.items else []),
        )
        for prop in properties or []
    ]


def round_trip(contract_file: Path, tmp_path: Path):
    """Export the contract to Pydantic models and import the result back."""
    exported = DataContract(data_contract_file=str(contract_file)).export("pydantic-model")
    generated = tmp_path / "generated_models.py"
    generated.write_text(exported)
    return exported, DataContract.import_from_source("pydantic-model", str(generated))


@pytest.mark.parametrize("contract_file", EXAMPLES)
def test_every_example_contract_survives_the_round_trip(contract_file, tmp_path):
    # The exporter inlines authoritativeDefinitions, so compare against the same view of the contract.
    original = resolve.resolve_data_contract(data_contract_location=str(contract_file), inline_references=True)
    _, reimported = round_trip(contract_file, tmp_path)

    assert [schema.name.lower() for schema in reimported.schema_] == [
        # The exporter names the class after the schema, capitalized, because a
        # Python class is CapWords: `orders` is exported as `class Orders`.
        schema.name.lower()
        for schema in original.schema_
    ]
    for before, after in zip(original.schema_, reimported.schema_):
        assert shape(after.properties) == shape(before.properties)


@pytest.mark.parametrize("contract_file", EXAMPLES)
def test_the_exported_module_is_valid_python(contract_file, tmp_path):
    exported, _ = round_trip(contract_file, tmp_path)

    ast.parse(exported)


@pytest.mark.parametrize("contract_file", EXAMPLES)
def test_the_round_trip_reaches_a_fixed_point(contract_file, tmp_path):
    """A second lap must not drift: whatever the first lap settled on is stable."""
    first_module, first_contract = round_trip(contract_file, tmp_path)

    contract_file_again = tmp_path / "first_lap.odcs.yaml"
    contract_file_again.write_text(first_contract.to_yaml())
    second_module, _ = round_trip(contract_file_again, tmp_path)

    assert second_module == first_module
