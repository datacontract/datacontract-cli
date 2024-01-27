import os

from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract

runner = CliRunner()


def test_valid_cli():
    current_file_path = os.path.abspath(__file__)
    print("DEBUG Current file path:" + current_file_path)

    result = runner.invoke(app, ["test",
                                 "./examples/parquet/datacontract.yaml"])
    assert result.exit_code == 0
    assert "Testing ./examples/parquet/datacontract.yaml" in result.stdout


def test_valid():
    data_contract = DataContract(
        data_contract_file="./examples/parquet/datacontract.yaml",
        # publish=True,
    )
    run = data_contract.test()
    print(run)
    assert run.result == "passed"
    assert len(run.checks) == 4
    assert all(check.result == "passed" for check in run.checks)
