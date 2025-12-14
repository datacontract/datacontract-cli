import yaml
from open_data_contract_standard.model import OpenDataContractStandard
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.export.protobuf_exporter import to_protobuf

# logging.basicConfig(level=logging.DEBUG, force=True)


def test_cli():
    runner = CliRunner()
    result = runner.invoke(app, ["export", "./fixtures/protobuf/datacontract.yaml", "--format", "protobuf"])
    assert result.exit_code == 0


def test_to_protobuf():
    odcs_yaml = """
kind: DataContract
apiVersion: v3.1.0
id: test_protobuf
schema:
  - name: Product
    description: Details of Product.
    properties:
      - name: category
        logicalType: string
        description: Enum field category
        customProperties:
          - property: enumValues
            value:
              CATEGORY_UNKNOWN: 0
              CATEGORY_ELECTRONICS: 1
              CATEGORY_CLOTHING: 2
              CATEGORY_HOME_APPLIANCES: 3
      - name: id
        logicalType: string
        description: Field id
      - name: name
        logicalType: string
        description: Field name
      - name: price
        logicalType: number
        description: Field price
      - name: reviews
        logicalType: array
        description: List of Review
        items:
          name: item
          logicalType: string
      - name: tags
        logicalType: string
        description: Field tags
  - name: Review
    description: Details of Review.
    properties:
      - name: comment
        logicalType: string
        description: Field comment
      - name: rating
        logicalType: integer
        description: Field rating
      - name: user
        logicalType: string
        description: Field user
"""
    data_contract = OpenDataContractStandard(**yaml.safe_load(odcs_yaml))

    expected_protobuf = """
syntax = "proto3";

package example;

// Enum for Category
enum Category {
  CATEGORY_UNKNOWN = 0;
  CATEGORY_ELECTRONICS = 1;
  CATEGORY_CLOTHING = 2;
  CATEGORY_HOME_APPLIANCES = 3;
}

// Details of Product.
message Product {
  // Enum field category
  Category category = 1;
  // Field id
  string id = 2;
  // Field name
  string name = 3;
  // Field price
  double price = 4;
  // List of Review
  repeated string reviews = 5;
  // Field tags
  string tags = 6;
}

// Details of Review.
message Review {
  // Field comment
  string comment = 1;
  // Field rating
  int32 rating = 2;
  // Field user
  string user = 3;
}

""".strip()

    result = to_protobuf(data_contract).strip()

    assert result == expected_protobuf
