from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.export.protobuf_converter import to_protobuf
from datacontract.model.data_contract_specification import DataContractSpecification

# logging.basicConfig(level=logging.DEBUG, force=True)


def test_cli():
    runner = CliRunner()
    result = runner.invoke(app, ["export", "./fixtures/export/datacontract.yaml", "--format", "protobuf"])
    assert result.exit_code == 0


def test_to_protobuf():
    data_contract = DataContractSpecification.from_file("fixtures/export/datacontract.yaml")
    expected_protobuf = """
syntax = "proto3";

/* The orders model */
message Orders {
  string order_id = 1;
  /* The order_total field */
  int64 order_total = 2;
  string order_status = 3;
}
""".strip()

    result = to_protobuf(data_contract).strip()

    assert result == expected_protobuf


def test_to_protobuf_nested():
    data_contract = DataContractSpecification.from_file("fixtures/export/datacontract_nested.yaml")
    expected_protobuf = """
syntax = "proto3";

/* The orders model */
message Orders {
  string order_id = 1;
  /* The order_total field */
  int64 order_total = 2;
  string order_status = 3;
  message Address {
    optional string street = 1;
    optional string city = 2;
  }
  optional Address address = 4;
}
""".strip()

    result = to_protobuf(data_contract).strip()

    assert result == expected_protobuf
