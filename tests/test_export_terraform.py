from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.export.terraform_converter import to_terraform
from datacontract.model.data_contract_specification import DataContractSpecification

# logging.basicConfig(level=logging.DEBUG, force=True)


def test_cli():
    runner = CliRunner()
    result = runner.invoke(app, ["export", "./fixtures/export/datacontract_s3.yaml", "--format", "terraform"])
    assert result.exit_code == 0


def test_to_terraform():
    data_contract = DataContractSpecification.from_file("fixtures/export/datacontract_s3.yaml")
    expected_terraform_file = """
resource "aws_s3_bucket" "orders-unit-test_production" {
  bucket = "datacontract-example-orders-latest"

  tags = {
    Name         = "Orders Unit Test"
    DataContract = "orders-unit-test"
    Server       = "production"
    DataProduct  = "orders"
  }
}
""".strip()

    result = to_terraform(data_contract)

    assert result == expected_terraform_file
