from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract

runner = CliRunner()


def test_cli():
    result = runner.invoke(app, ["test", "--file", "./examples/local-json/datacontract.yaml"])
    # Skip assertion https://github.com/sodadata/soda-core/issues/1992
    # assert result.exit_code == 0


def test_local_json():
    data_contract = DataContract(data_contract_file="examples/local-json/datacontract.yaml")
    run = data_contract.test()
    print(run)
    # Skip assertion https://github.com/sodadata/soda-core/issues/1992
    # assert run.result == "passed"


