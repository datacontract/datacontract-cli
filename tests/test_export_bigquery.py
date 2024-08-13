import json
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract

# logging.basicConfig(level=logging.DEBUG, force=True)


def test_cli():
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "export",
            "--format",
            "bigquery",
            "--server",
            "bigquery",
            "fixtures/bigquery/export/datacontract.yaml",
        ],
    )
    assert result.exit_code == 0


def test_exports_bigquery_schema():
    data_contract_file: str = "fixtures/bigquery/export/datacontract.yaml"
    with open(data_contract_file) as file:
        file_content = file.read()
    data_contract = DataContract(data_contract_str=file_content, server="bigquery")
    assert data_contract.lint(enabled_linters="none").has_passed()
    result = data_contract.export("bigquery")

    print("Result:\n", result)
    with open("fixtures/bigquery/export/bq_table_schema.json") as file:
        expected = file.read()
    assert json.loads(result) == json.loads(expected)
