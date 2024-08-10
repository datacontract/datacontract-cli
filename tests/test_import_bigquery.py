import yaml
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract
from datacontract.imports.bigquery_importer import import_bigquery_from_json

# logging.basicConfig(level=logging.DEBUG, force=True)


def test_cli():
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "import",
            "--format",
            "bigquery",
            "--source",
            "fixtures/bigquery/import/complete_table_schema.json",
        ],
    )
    assert result.exit_code == 0


def test_import_bigquery_schema():
    result = DataContract().import_from_source("bigquery", "fixtures/bigquery/import/complete_table_schema.json")

    print("Result:\n", result.to_yaml())
    with open("fixtures/bigquery/import/datacontract.yaml") as file:
        expected = file.read()
    assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected)
    assert DataContract(data_contract_str=expected).lint(enabled_linters="none").has_passed()


def test_import_multiple_bigquery_schemas_with_different_types():
    result = DataContract().import_from_source("bigquery", "fixtures/bigquery/import/multi_import_table.json")

    result = import_bigquery_from_json(result, "fixtures/bigquery/import/multi_import_external_table.json")
    result = import_bigquery_from_json(result, "fixtures/bigquery/import/multi_import_snapshot.json")
    result = import_bigquery_from_json(result, "fixtures/bigquery/import/multi_import_view.json")
    result = import_bigquery_from_json(result, "fixtures/bigquery/import/multi_import_materialized_view.json")

    print("Result:\n", result.to_yaml())
    with open("fixtures/bigquery/import/datacontract_multi_import.yaml") as file:
        expected = file.read()
    assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected)
    assert DataContract(data_contract_str=expected).lint(enabled_linters="none").has_passed()
