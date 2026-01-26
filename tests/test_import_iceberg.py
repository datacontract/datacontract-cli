import pytest
import yaml
from pyiceberg.schema import Schema
from pyiceberg.types import IntegerType, NestedField
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.imports.iceberg_importer import load_and_validate_iceberg_schema
from datacontract.model.exceptions import DataContractException

expected = """
version: 1.0.0
kind: DataContract
apiVersion: v3.1.0
id: my-data-contract
name: My Data Contract
status: draft
schema:
  - name: test-table
    physicalType: table
    logicalType: object
    physicalName: test-table
    properties:
      - name: foo
        logicalType: string
        physicalType: string
        customProperties:
          - property: icebergFieldId
            value: 1
      - name: bar
        logicalType: integer
        physicalType: int
        primaryKey: true
        primaryKeyPosition: 1
        required: true
        customProperties:
          - property: icebergFieldId
            value: 2
      - name: baz
        logicalType: boolean
        physicalType: boolean
        customProperties:
          - property: icebergFieldId
            value: 3
      - name: qux
        logicalType: array
        physicalType: list<string>
        required: true
        items:
          name: items
          logicalType: string
          physicalType: string
          required: true
        customProperties:
          - property: icebergFieldId
            value: 4
      - name: quux
        logicalType: object
        physicalType: map
        required: true
        customProperties:
          - property: icebergFieldId
            value: 6
          - property: mapKeyType
            value: string
          - property: mapValueType
            value: object
          - property: mapValueRequired
            value: 'true'
          - property: mapValuePhysicalType
            value: map
          - property: mapNestedKeyType
            value: string
          - property: mapNestedValueType
            value: integer
          - property: mapNestedValueRequired
            value: 'true'
      - name: location
        logicalType: array
        physicalType: 'list<struct<13: latitude: optional float, 14: longitude: optional float>>'
        required: true
        items:
          name: items
          logicalType: object
          physicalType: 'struct<13: latitude: optional float, 14: longitude: optional float>'
          required: true
          properties:
            - name: latitude
              logicalType: number
              physicalType: float
              customProperties:
                - property: icebergFieldId
                  value: 13
            - name: longitude
              logicalType: number
              physicalType: float
              customProperties:
                - property: icebergFieldId
                  value: 14
        customProperties:
          - property: icebergFieldId
            value: 11
      - name: person
        logicalType: object
        physicalType: 'struct<16: name: optional string, 17: age: required int>'
        properties:
          - name: name
            logicalType: string
            physicalType: string
            customProperties:
              - property: icebergFieldId
                value: 16
          - name: age
            logicalType: integer
            physicalType: int
            required: true
            customProperties:
              - property: icebergFieldId
                value: 17
        customProperties:
          - property: icebergFieldId
            value: 15
    """


def test_cli():
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "import",
            "--format",
            "iceberg",
            "--source",
            "fixtures/iceberg/nested_schema.json",
            "--iceberg-table",
            "test-table",
        ],
    )

    output = result.stdout
    assert result.exit_code == 0
    assert yaml.safe_load(output) == yaml.safe_load(expected)


def test_load_and_validate_iceberg_schema_success():
    s = load_and_validate_iceberg_schema("fixtures/iceberg/simple_schema.json")

    assert s == Schema(
        NestedField(field_id=1, name="foo", field_type=IntegerType(), required=True),
        schema_id=1,
        identifier_field_ids=[1],
    )


def test_load_and_validate_iceberg_schema_failure():
    with pytest.raises(DataContractException):
        load_and_validate_iceberg_schema("fixtures/iceberg/invalid_schema.json")
