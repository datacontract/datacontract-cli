import logging

from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract

logging.basicConfig(level=logging.INFO, force=True)

runner = CliRunner()


def test_lint_valid_data_contract():
    data_contract_file = "examples/lint/valid_datacontract.yaml"
    data_contract = DataContract(data_contract_file=data_contract_file)

    run = data_contract.lint()

    assert run.result == "passed"


def test_lint_invalid_data_contract():
    data_contract_file = "examples/lint/invalid_datacontract.yaml"
    data_contract = DataContract(data_contract_file=data_contract_file)

    run = data_contract.lint()

    assert run.result == "failed"


def test_lint_cli_valid():
    data_contract_file = "examples/lint/valid_datacontract.yaml"
    expected_output = "🟢 data contract is valid. Run 1 checks.\n"

    result = runner.invoke(app, ["lint", data_contract_file])

    assert result.exit_code == 0
    assert expected_output in result.stdout


def test_lint_cli_invalid():
    data_contract_file = "examples/lint/invalid_datacontract.yaml"
    expected_output = "🔴 data contract is invalid, found the following errors:\n1) data must contain ['id'] properties\n"

    result = runner.invoke(app, ["lint", data_contract_file])

    assert result.exit_code == 1
    assert expected_output in result.stdout
