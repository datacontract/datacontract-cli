import logging

from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract

logging.basicConfig(level=logging.DEBUG, force=True)


def test_cli():
    runner = CliRunner()
    result = runner.invoke(app, ["export", "./fixtures/dbml/datacontract.yaml", "--format", "dbml"])
    assert result.exit_code == 0


def test_dbml_export():
    data_contract = DataContract(data_contract_file="fixtures/dbml/datacontract.yaml")
    assert data_contract.lint(enabled_linters="none").has_passed()
    
    result = data_contract.export("dbml")

    with open("fixtures/dbml/export.dbml") as file:
        expected = file.read()
    
    assert result.strip() == expected.strip()
