import json

from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract
from datacontract.export.jsonschema_converter import to_jsonschemas

# logging.basicConfig(level=logging.DEBUG, force=True)


def test_import_cli():
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "import",
            "--format",
            "jsonschema",
            "--source",
            "fixtures/import/orders.json",
        ],
    )
    assert result.exit_code == 0


def test_export_cli():
    runner = CliRunner()
    result = runner.invoke(app, ["export", "./fixtures/local-json/datacontract.yaml", "--format", "jsonschema"])
    assert result.exit_code == 0


def test_roundtrip_json_schema_orders():
    # Import the data contract from the JSON schema source
    result_import = DataContract().import_from_source("jsonschema", "fixtures/import/orders.json")

    # Create a data contract specification with inline definitions
    data_contract = DataContract(
        data_contract_str=result_import.to_yaml(), inline_definitions=True
    ).get_data_contract_specification()

    # Load the expected result from the JSON file
    with open("fixtures/import/orders.json", "r") as f:
        expected_result = json.load(f)

    # Export the data contract to JSON schema
    exported_jsonschema = to_jsonschemas(data_contract)

    # Compare the exported JSON schema with the expected result
    assert exported_jsonschema["OrderSchema"] == expected_result
