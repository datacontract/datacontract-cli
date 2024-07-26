import os

from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract

runner = CliRunner()


def test_valid_cli():
    current_file_path = os.path.abspath(__file__)
    print("DEBUG Current file path:" + current_file_path)

    result = runner.invoke(app, ["test", "./fixtures/local-delta/datacontract.yaml"])
    assert result.exit_code == 0
    assert "Testing ./fixtures/local-delta/datacontract.yaml" in result.stdout


def test_valid():
    data_contract = DataContract(
        data_contract_file="fixtures/local-delta/datacontract.yaml",
        # publish=True,
    )
    run = data_contract.test()
    print(run.pretty())
    assert run.result == "passed"
    assert len(run.checks) == 9
    assert all(check.result == "passed" for check in run.checks)
