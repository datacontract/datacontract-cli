import json

from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract
from datacontract.export.jsonschema_exporter import to_jsonschemas

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
    # Import JSON schema → returns ODCS
    odcs = DataContract.import_from_source("jsonschema", "fixtures/import/orders.json")

    # Load the expected result from the JSON file
    with open("fixtures/import/orders.json", "r") as f:
        expected_result = json.load(f)

    # Export ODCS back to JSON schema
    exported_jsonschema = to_jsonschemas(odcs)

    # Compare the exported JSON schema with the expected result
    assert exported_jsonschema["OrderSchema"] == expected_result
