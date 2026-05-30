from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract
from datacontract.model.run import ResultEnum

runner = CliRunner()


def test_test_nonexistent_server_exits_with_error():
    data_contract = DataContract(
        data_contract_file="fixtures/local-json/datacontract.yaml",
        server="nonexistent",
    )
    run = data_contract.test()
    assert run.result == ResultEnum.failed
    assert any("nonexistent" in check.reason for check in run.checks)


def test_test_nonexistent_server_cli_exit_code():
    result = runner.invoke(
        app,
        ["test", "--server", "nonexistent", "./fixtures/local-json/datacontract.yaml"],
    )
    assert result.exit_code == 1
