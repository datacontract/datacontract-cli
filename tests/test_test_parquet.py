import os

from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract

runner = CliRunner()


def test_valid_cli():
    current_file_path = os.path.abspath(__file__)
    print("DEBUG Current file path:" + current_file_path)

    result = runner.invoke(app, ["test", "./fixtures/parquet/datacontract.yaml"])
    assert result.exit_code == 0
    assert "Testing ./fixtures/parquet/datacontract.yaml" in result.stdout


def test_valid():
    data_contract = DataContract(
        data_contract_file="fixtures/parquet/datacontract.yaml",
        # publish=True,
    )
    run = data_contract.test()
    print(run.pretty())
    assert run.result == "passed"
    assert len(run.checks) == 4
    assert all(check.result == "passed" for check in run.checks)


def test_invalid():
    data_contract = DataContract(
        data_contract_file="fixtures/parquet/datacontract_invalid.yaml",
    )
    run = data_contract.test()
    print(run.pretty())
    assert run.result == "failed"
    assert len(run.checks) == 6
    assert any(check.result == "failed" for check in run.checks)
    assert any(check.reason == "Type Mismatch, Expected Type: DATE; Actual Type: varchar" for check in run.checks)


def test_timestamp():
    data_contract = DataContract(
        data_contract_file="fixtures/parquet/datacontract_timestamp.yaml",
    )
    run = data_contract.test()
    print(run.pretty())
    assert run.result == "passed"


def test_decimal():
    data_contract = DataContract(
        data_contract_file="fixtures/parquet/datacontract_decimal.yaml",
    )
    run = data_contract.test()
    print(run.pretty())
    assert run.result == "passed"
