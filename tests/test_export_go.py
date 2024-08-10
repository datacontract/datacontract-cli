from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract

# logging.basicConfig(level=logging.DEBUG, force=True)


def test_cli():
    runner = CliRunner()
    result = runner.invoke(app, ["export", "./fixtures/export/datacontract.yaml", "--format", "go"])
    assert result.exit_code == 0


def test_to_go_types():
    actual = DataContract(data_contract_file="fixtures/export/datacontract.yaml").export("go")
    expected = """
package main


type Orders struct {
    OrderId varchar `json:"order_id" avro:"order_id"`  // None
    OrderTotal bigint `json:"order_total" avro:"order_total"`  // The order_total field
    OrderStatus string `json:"order_status" avro:"order_status"`  // None
}

"""
    assert actual.strip() == expected.strip()
