from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.export.protobuf_converter import to_protobuf
from datacontract.model.data_contract_specification import DataContractSpecification

# logging.basicConfig(level=logging.DEBUG, force=True)


def test_cli():
    runner = CliRunner()
    result = runner.invoke(app, ["export", "./fixtures/protobuf/datacontract.yaml", "--format", "protobuf"])
    assert result.exit_code == 0


def test_to_protobuf():
    data_contract = DataContractSpecification.from_file("fixtures/protobuf/datacontract.yaml")
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
