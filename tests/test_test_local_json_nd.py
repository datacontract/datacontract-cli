from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract
from tests.dcs_deprecation import assert_dcs_deprecation_is_the_only_warning

runner = CliRunner()


def test_cli():
    result = runner.invoke(app, ["test", "./fixtures/local-json-nd/datacontract.yaml", "--logs"])
    print(result.stdout)
    assert result.exit_code == 0


def test_local_json():
    data_contract = DataContract(data_contract_file="fixtures/local-json-nd/datacontract.yaml")
    run = data_contract.test()
    print(run.pretty())
    assert_dcs_deprecation_is_the_only_warning(run)
