"""XML Schema to data contract and back: what one direction writes, the other reads the same way."""

import glob
import logging
from pathlib import Path

import pytest
import xmlschema

from datacontract.data_contract import DataContract
from datacontract.export.xsd_exporter import to_xsd
from datacontract.imports.xsd_importer import import_xsd

CONTRACT = """
apiVersion: v3.2.0
kind: DataContract
id: shop
name: orders
version: 1.0.0
status: active
schema:
  - name: orders
    physicalType: object
    description: |-
      An order placed in the webshop.
      One per checkout.
    customProperties:
      - property: xmlNamespace
        value: urn:example:shop
    properties:
      - name: order_id
        logicalType: string
        description: Unique identifier of the order.
        required: true
        logicalTypeOptions:
          pattern: ^(ORD-[0-9]{4})$
          maxLength: 8
      - name: placed_at
        logicalType: timestamp
        required: true
      - name: delivery_date
        logicalType: date
        logicalTypeOptions:
          minimum: "2020-01-01"
      - name: total
        logicalType: number
        required: true
        logicalTypeOptions:
          minimum: 0
          exclusiveMaximum: 100000.5
        customProperties:
          - property: precision
            value: 10
          - property: scale
            value: 2
      - name: status
        logicalType: string
        required: true
        enum:
          - value: pending
          - value: shipped
      - name: rating
        logicalType: integer
        enum:
          - value: 1
          - value: 2
          - value: 3
      - name: gift
        logicalType: boolean
      - name: customer
        logicalType: object
        required: true
        properties:
          - name: name
            logicalType: string
            required: true
          - name: id
            logicalType: string
            required: true
            customProperties:
              - property: xmlNode
                value: attribute
      - name: lines
        logicalType: array
        required: true
        logicalTypeOptions:
          minItems: 2
          maxItems: 50
        items:
          logicalType: object
          properties:
            - name: sku
              logicalType: string
              required: true
            - name: price
              logicalType: object
              required: true
              properties:
                - name: value
                  logicalType: number
                  logicalTypeOptions:
                    minimum: 0
                  customProperties:
                    - property: xmlNode
                      value: text
                - name: currency
                  logicalType: string
                  required: true
                  customProperties:
                    - property: xmlNode
                      value: attribute
      - name: notes
        logicalType: array
        items:
          logicalType: string
      - name: extension
        logicalType: object
"""


def roundtrip(contract, tmp_path: Path):
    source = tmp_path / "schema.xsd"
    source.write_text(to_xsd(contract))
    return import_xsd(str(source))


def essentials(properties) -> list:
    """What a contract says about its properties, without the physical types the XSD import fills in."""
    return [
        {
            "name": p.name,
            "logicalType": p.logicalType,
            "required": bool(p.required),
            "description": p.description,
            "logicalTypeOptions": p.logicalTypeOptions,
            "enum": [e.value for e in p.enum or []],
            "customProperties": {c.property: str(c.value) for c in p.customProperties or []},
            "properties": essentials(p.properties or []),
            "items": essentials([p.items]) if p.items else None,
        }
        for p in properties
    ]


def test_contract_to_xsd_and_back(tmp_path: Path):
    contract = DataContract(data_contract_str=CONTRACT).get_data_contract()

    result = roundtrip(contract, tmp_path)

    (expected,), (actual,) = contract.schema_, result.schema_
    assert (actual.name, actual.description, actual.customProperties) == (
        expected.name,
        expected.description,
        expected.customProperties,
    )
    expected_properties = essentials(expected.properties)
    # The items of an array are named items after the import
    for prop in expected_properties:
        for item in prop["items"] or []:
            item["name"] = "items"
    assert essentials(actual.properties) == expected_properties


@pytest.mark.parametrize("fixture", ["orders", "purchase-order"])
def test_xsd_to_contract_and_back(fixture, tmp_path: Path):
    imported = DataContract.import_from_source("xsd", f"fixtures/import/xsd/{fixture}.xsd")

    assert roundtrip(imported, tmp_path).model_dump() == imported.model_dump()


def test_exported_xsd_validates_the_documents_of_the_imported_one():
    original = xmlschema.XMLSchema("fixtures/import/xsd/orders.xsd")
    exported = xmlschema.XMLSchema(to_xsd(DataContract.import_from_source("xsd", "fixtures/import/xsd/orders.xsd")))

    for document in sorted(glob.glob("fixtures/xml/data/*.xml")) + sorted(glob.glob("fixtures/xml/invalid/*.xml")):
        assert exported.is_valid(document) == original.is_valid(document), document
    assert not exported.is_valid("fixtures/xml/invalid/order-3.xml")


CONTRACTS = sorted(
    set(glob.glob("fixtures/**/*.yaml", recursive=True) + glob.glob("fixtures/**/*.yml", recursive=True))
)


@pytest.mark.parametrize("path", CONTRACTS)
def test_every_contract_exports_to_a_valid_xsd_that_imports_back_to_itself(path, tmp_path: Path, caplog):
    """Export, import and export again; the second XSD has to be the first."""
    try:
        contract = DataContract(data_contract_file=path).get_data_contract()
    except Exception:
        pytest.skip("not a data contract")
    if not contract.schema_:
        pytest.skip("no schema")

    with caplog.at_level(logging.ERROR):
        first = to_xsd(contract)
        xmlschema.XMLSchema(first)
        second = to_xsd(roundtrip(contract, tmp_path))

    assert second == first


def test_a_plain_contract_to_xsd_and_back_keeps_its_structure_and_constraints(tmp_path: Path):
    from tests.test_export_xsd import PLAIN_CONTRACT

    contract = DataContract(data_contract_str=PLAIN_CONTRACT).get_data_contract()

    (actual,) = roundtrip(contract, tmp_path).schema_
    props = {p.name: p for p in actual.properties}

    # no XML custom properties appear where the contract had none
    assert actual.customProperties is None
    assert all(p.customProperties is None for p in props.values())
    assert actual.description == "One row per customer."
    assert [(p.name, p.logicalType, bool(p.required)) for p in actual.properties] == [
        ("customer_id", "string", True),
        ("email", "string", False),
        ("signed_up_at", "timestamp", True),
        ("birthday", "date", False),
        ("lifetime_value", "number", False),
        ("orders", "integer", False),
        ("active", "boolean", True),
        ("address", "object", False),
        ("phone_numbers", "array", False),
        ("segment", "string", False),
    ]
    assert props["lifetime_value"].logicalTypeOptions == {"minimum": 0}
    assert [e.value for e in props["segment"].enum] == ["retail", "business"]
    assert [(p.name, bool(p.required)) for p in props["address"].properties] == [("street", False), ("city", True)]
    # what XML Schema cannot say: SQL physical types, the primary key, and string formats
    assert props["customer_id"].physicalType == "string" and not props["customer_id"].primaryKey
    assert props["email"].logicalTypeOptions == {"maxLength": 320}
    # XSD patterns match the whole value, so the anchored pattern comes back anchored
    assert props["phone_numbers"].items.logicalTypeOptions == {"pattern": "^(\\+[0-9 ]+)$"}


def test_an_xsd_with_every_supported_construct_comes_back_byte_for_byte(tmp_path: Path):
    """Import and export again: the schema is the one that went in, character for character."""
    original = Path("fixtures/xsd/canonical.xsd").read_text()
    xmlschema.XMLSchema(original)

    imported = import_xsd("fixtures/xsd/canonical.xsd")

    assert to_xsd(imported) == original
    # and the contract it imports to survives the next round as well
    assert roundtrip(imported, tmp_path).model_dump() == imported.model_dump()
