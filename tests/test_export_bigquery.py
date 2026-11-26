import json

from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract
from datacontract.export.bigquery_exporter import to_bigquery_schema
from datacontract.export.exporter import ExportFormat
from datacontract.imports.bigquery_importer import import_bigquery_from_json
from datacontract.model.odcs import BIGQUERY_TABLE_VALUED_FUNCTION

# logging.basicConfig(level=logging.DEBUG, force=True)


def test_cli():
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "export",
            "bigquery",
            "fixtures/bigquery/export/datacontract.odcs.yaml",
            "--server",
            "bigquery",
        ],
    )
    assert result.exit_code == 0


def test_exports_bigquery_schema():
    data_contract_file: str = "fixtures/bigquery/export/datacontract.odcs.yaml"
    with open(data_contract_file) as file:
        file_content = file.read()
    data_contract = DataContract(data_contract_str=file_content, server="bigquery")
    assert data_contract.lint().has_passed()
    result = data_contract.export(ExportFormat.bigquery)

    print("Result:\n", result)
    with open("fixtures/bigquery/export/bq_table_schema.json") as file:
        expected = file.read()
    assert json.loads(result) == json.loads(expected)


def test_exports_bigquery_table_valued_function():
    odcs = import_bigquery_from_json("fixtures/bigquery/import/multi_import_table_valued_function.json")

    result = to_bigquery_schema(odcs.schema_[0], odcs.servers[0])

    assert result["type"] == BIGQUERY_TABLE_VALUED_FUNCTION
    assert result["arguments"] == [
        {"name": "start_ts", "dataType": {"typeKind": "TIMESTAMP"}},
        {"name": "ids", "dataType": {"typeKind": "ARRAY"}},
    ]
