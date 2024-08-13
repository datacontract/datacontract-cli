from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract

runner = CliRunner()

# logging.basicConfig(level=logging.DEBUG, force=True)


def test_cli():
    result = runner.invoke(app, ["test", "--examples", "./fixtures/examples/datacontract_missing.yaml"])
    assert result.exit_code == 1


def test_missing():
    data_contract = DataContract(data_contract_file="fixtures/examples/datacontract_missing.yaml", examples=True)
    run = data_contract.test()
    print(run)
    print(run.result)
    assert run.result == "warning"
