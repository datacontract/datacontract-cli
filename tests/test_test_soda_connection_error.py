from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract
from datacontract.model.run import ResultEnum

runner = CliRunner()

CONTRACT = "fixtures/soda-connection-error/datacontract.yaml"


def test_soda_connection_error_result_is_failed(monkeypatch):
    monkeypatch.setenv("DATACONTRACT_POSTGRES_USERNAME", "u")
    monkeypatch.setenv("DATACONTRACT_POSTGRES_PASSWORD", "p")

    run = DataContract(data_contract_file=CONTRACT).test()

    assert run.result == ResultEnum.failed
    assert any(check.result == ResultEnum.failed and check.engine == "soda-core" for check in run.checks), (
        "Expected a failed soda-core check for the unreachable server"
    )


def test_soda_connection_error_cli_exit_code(monkeypatch):
    monkeypatch.setenv("DATACONTRACT_POSTGRES_USERNAME", "u")
    monkeypatch.setenv("DATACONTRACT_POSTGRES_PASSWORD", "p")

    result = runner.invoke(app, ["test", CONTRACT])

    assert result.exit_code == 1, (
        f"Expected exit_code 1 for a connection failure, got {result.exit_code}. stdout:\n{result.stdout}"
    )
