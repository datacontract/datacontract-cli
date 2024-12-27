from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract

runner = CliRunner()

# logging.basicConfig(level=logging.DEBUG, force=True)


def test_cli():
    result = runner.invoke(app, ["test", "--examples", "./fixtures/examples/datacontract_csv.yaml"])
    assert result.exit_code == 0


def test_csv():
    data_contract = DataContract(data_contract_file="fixtures/examples/datacontract_csv.yaml", examples=True)
    run = data_contract.test()
    print(run)
    print(run.result)
    assert run.result == "passed"


# fixtures/s3-json-remote/datacontract.yaml: uses new examples structure.
# def test_csv_orders():
#     data_contract = DataContract(data_contract_file="fixtures/s3-json-remote/datacontract.yaml", examples=True)
#     run = data_contract.test()
#     print(run)
#     print(run.result)
#     assert run.result == "passed"
