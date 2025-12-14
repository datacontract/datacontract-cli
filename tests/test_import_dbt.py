import yaml
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract
from datacontract.imports.dbt_importer import read_dbt_manifest

# logging.basicConfig(level=logging.DEBUG, force=True)

dbt_manifest = "fixtures/dbt/import/manifest_jaffle_duckdb.json"
dbt_manifest_bigquery = "fixtures/dbt/import/manifest_jaffle_bigquery.json"
dbt_manifest_empty_columns = "fixtures/dbt/import/manifest_empty_columns.json"


def test_read_dbt_manifest_():
    result = read_dbt_manifest(dbt_manifest)
    assert len([node for node in result.nodes.values() if node.resource_type == "model"]) == 5


def test_cli():
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "import",
            "--format",
            "dbt",
            "--source",
            dbt_manifest,
        ],
    )
    assert result.exit_code == 0


def test_cli_bigquery():
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "import",
            "--format",
            "dbt",
            "--source",
            dbt_manifest_bigquery,
        ],
    )
    assert result.exit_code == 0


def test_cli_with_filter():
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "import",
            "--format",
            "dbt",
            "--source",
            dbt_manifest,
            "--dbt-model",
            "customers",
            "--dbt-model",
            "orders",
        ],
    )
    assert result.exit_code == 0


def test_import_dbt_manifest():
    result = DataContract.import_from_source("dbt", dbt_manifest)

    print("Result:\n", result.to_yaml())
    with open("fixtures/dbt/import/expected/manifest_jaffle_duckdb.odcs.yaml") as file:
        expected = file.read()
    assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected)


def test_import_dbt_manifest_bigquery():
    result = DataContract.import_from_source("dbt", dbt_manifest_bigquery)

    print("Result:\n", result.to_yaml())
    with open("fixtures/dbt/import/expected/manifest_jaffle_bigquery.odcs.yaml") as file:
        expected = file.read()
    assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected)


def test_import_dbt_manifest_with_filter_and_empty_columns():
    result = DataContract.import_from_source("dbt", dbt_manifest_empty_columns, dbt_model=["customers"])

    print("Result:\n", result.to_yaml())
    with open("fixtures/dbt/import/expected/manifest_empty_columns_filtered.odcs.yaml") as file:
        expected = file.read()
    assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected)


def test_import_dbt_manifest_with_filter():
    result = DataContract.import_from_source("dbt", dbt_manifest, dbt_model=["customers"])

    print("Result:\n", result.to_yaml())
    with open("fixtures/dbt/import/expected/manifest_jaffle_duckdb_filtered.odcs.yaml") as file:
        expected = file.read()
    assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected)
