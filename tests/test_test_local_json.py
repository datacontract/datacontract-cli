import pytest
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract

runner = CliRunner()


@pytest.mark.skip(reason="https://github.com/sodadata/soda-core/issues/1992")
def _test_cli():
    result = runner.invoke(app, ["test", "./fixtures/local-json/datacontract.yaml"])
    assert result.exit_code == 0


@pytest.mark.skip(reason="https://github.com/sodadata/soda-core/issues/1992")
def _test_local_json():
    data_contract = DataContract(data_contract_file="fixtures/local-json/datacontract.yaml")
    run = data_contract.test()
    print(run)
    assert run.result == "passed"
