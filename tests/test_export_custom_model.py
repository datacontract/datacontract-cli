from pathlib import Path

from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract


def test_cli():
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "export",
            "./fixtures/custom/export_model/datacontract.odcs.yaml",
            "--format",
            "custom",
            "--template",
            "./fixtures/custom/export_model/template.sql",
            "--schema-name",
            "users",
        ],
    )
    assert result.exit_code == 0


def test_export_custom_schema_name():
    path_fixtures = Path("fixtures/custom/export_model")

    data_contract = DataContract(data_contract_file=str(path_fixtures / "datacontract.odcs.yaml"))
    template = path_fixtures / "template.sql"

    result = data_contract.export(export_format="custom", schema_name="users", template=template)

    with open(path_fixtures / "expected.sql", "r") as file:
        assert result == file.read()
