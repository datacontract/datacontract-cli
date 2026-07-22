import pytest
import yaml
from open_data_contract_standard.model import OpenDataContractStandard
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.export.protobuf_exporter import to_protobuf
from datacontract.model.exceptions import DataContractException

# logging.basicConfig(level=logging.DEBUG, force=True)


def test_cli():
    runner = CliRunner()
    result = runner.invoke(app, ["export", "protobuf", "./fixtures/protobuf/datacontract.yaml"])
    assert result.exit_code == 0


def test_to_protobuf():
    odcs_yaml = """
kind: DataContract
apiVersion: v3.1.0
id: test_protobuf
customProperties:
  - property: protoPackageName
    value: com.example.mydata
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

      - name: users
        logicalType: array
        items:
          name: User
          logicalType: object
          properties:
          - name: id
            logicalType: string

      - name: geo_description
        logicalType: string
        required: false
        
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
      - name: sub_review
        description: Details of sub review.
        required: False
        logicalType: object
        properties:
          - name: comment
            logicalType: string
            description: Field comment
"""
    data_contract = OpenDataContractStandard(**yaml.safe_load(odcs_yaml))

    expected_protobuf = """
syntax = "proto3";

package com.example.mydata;

// Enum for Category
enum Category {
  CATEGORY_UNKNOWN = 0;
  CATEGORY_ELECTRONICS = 1;
  CATEGORY_CLOTHING = 2;
  CATEGORY_HOME_APPLIANCES = 3;
}

// Details of Product.
message Product {
  message User {
    string id = 1;
  }

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
  repeated User users = 6;
  optional string geo_description = 7;
  // Field tags
  string tags = 8;
}

// Details of Review.
message Review {
  // Details of sub review.
  message SubReview {
    // Field comment
    string comment = 1;
  }

  // Field comment
  string comment = 1;
  // Field rating
  int32 rating = 2;
  // Field user
  string user = 3;
  // Details of sub review.
  optional SubReview sub_review = 4;
}

    """.strip()
    result = to_protobuf(data_contract).strip()

    assert result == expected_protobuf


def test_to_protobuf_custom_package_name():
    odcs_yaml = """
kind: DataContract
apiVersion: v3.1.0
id: test_protobuf
customProperties:
  - property: protoPackageName
    value: com.example.product
schema:
  - name: Product
    properties:
      - name: id
        logicalType: string
"""
    data_contract = OpenDataContractStandard(**yaml.safe_load(odcs_yaml))

    result = to_protobuf(data_contract)

    assert "package com.example.product;\n" in result


def test_to_protobuf_invalid_package_name():
    odcs_yaml = """
kind: DataContract
apiVersion: v3.1.0
id: test_protobuf
customProperties:
  - property: protoPackageName
    value: "123 not a package!"
schema:
  - name: Product
    properties:
      - name: id
        logicalType: string
"""
    data_contract = OpenDataContractStandard(**yaml.safe_load(odcs_yaml))

    with pytest.raises(DataContractException):
        to_protobuf(data_contract)
