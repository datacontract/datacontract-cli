import pytest
from pyiceberg.schema import Schema
from pyiceberg.types import IntegerType, NestedField
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.imports.iceberg_importer import load_and_validate_iceberg_schema
from datacontract.model.exceptions import DataContractException

expected = """
dataContractSpecification: 1.1.0
id: my-data-contract-id
info:
  title: My Data Contract
  version: 0.0.1
models:
  test-table:
    type: table
    title: test-table
    fields:
      foo:
        title: foo
        type: string
        required: false
        config:
          icebergFieldId: 1
      bar:
        title: bar
        type: integer
        required: true
        primaryKey: true
        config:
          icebergFieldId: 2
      baz:
        title: baz
        type: boolean
        required: false
        config:
          icebergFieldId: 3
      qux:
        title: qux
        type: array
        required: true
        items:
          type: string
          required: true
        config:
          icebergFieldId: 4
      quux:
        title: quux
        type: map
        required: true
        keys:
          type: string
          required: true
        values:
          type: map
          required: true
          keys:
            type: string
            required: true
          values:
            type: integer
            required: true
        config:
          icebergFieldId: 6
      location:
        title: location
        type: array
        required: true
        items:
          type: object
          required: true
          fields:
            latitude:
              title: latitude
              type: float
              required: false
              config:
                icebergFieldId: 13
            longitude:
              title: longitude
              type: float
              required: false
              config:
                icebergFieldId: 14
        config:
          icebergFieldId: 11
      person:
        title: person
        type: object
        required: false
        fields:
          name:
            title: name
            type: string
            required: false
            config:
              icebergFieldId: 16
          age:
            title: age
            type: integer
            required: true
            config:
              icebergFieldId: 17
        config:
          icebergFieldId: 15
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
    assert output.strip() == expected.strip()


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
