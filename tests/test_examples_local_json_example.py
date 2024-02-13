import pytest
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract

runner = CliRunner()


def test_cli():
    result = runner.invoke(app, ["test", "--examples", "./examples/local-json-simple/datacontract.yaml"])
    assert result.exit_code == 0


def test_local_json():
    data_contract = DataContract(data_contract_file="examples/local-json-simple/datacontract.yaml")
    run = data_contract.testExample()
    print(run)
    print(run.result)
    assert run.result == "passed"


