import pytest
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract

runner = CliRunner()


def _test_cli():
    result = runner.invoke(app, ["test", "./fixtures/local-delta/datacontract.yaml"])
    assert result.exit_code == 0


def _test_local_delta():
    data_contract = DataContract(data_contract_file="fixtures/local-delta/datacontract.yaml")
    run = data_contract.test()
    print(run)
    assert run.result == "passed"
