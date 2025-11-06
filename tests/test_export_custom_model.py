from pathlib import Path

from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract
from datacontract.export.custom_converter import to_custom
from datacontract.model.data_contract_specification import DataContractSpecification

# logging.basicConfig(level=logging.DEBUG, force=True)


def test_cli():
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "export",
            "./fixtures/custom/export/datacontract.yaml",
            "--format",
            "custom",
            "--template",
            "./fixtures/custom/export/template.sql",
            "--model",
            "line_items",
        ],
    )
    assert result.exit_code == 0


def test_export_custom_model():
    path_fixtures = Path("fixtures/custom/export_model")

    data_contract = DataContract(data_contract_file=str(path_fixtures / "datacontract.yaml"))
    template = path_fixtures / "template.sql"

    result = data_contract.export(export_format="custom", model="line_items", template=template)

    with open(path_fixtures / "expected.sql", "r") as file:
        assert result == file.read()


def test_export_custom_model_stg():
    path_fixtures = Path("fixtures/custom/export_model")

    data_contract = DataContract(data_contract_file=str(path_fixtures / "datacontract.yaml"))
    template = path_fixtures / "template_stg.sql"

    result = data_contract.export(export_format="custom", model="line_items", template=template)
    print(result)

    with open(path_fixtures / "expected_stg.sql", "r") as file:
        assert result == file.read()
