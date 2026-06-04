import yaml
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract
from datacontract.imports.dbt_importer import read_dbt_manifest

# logging.basicConfig(level=logging.DEBUG, force=True)

dbt_manifest = "fixtures/dbt/import/manifest_jaffle_duckdb.json"
dbt_manifest_bigquery = "fixtures/dbt/import/manifest_jaffle_bigquery.json"
dbt_manifest_empty_columns = "fixtures/dbt/import/manifest_empty_columns.json"
dbt_manifest_versioned = "fixtures/dbt/import/manifest_versioned_models.json"


def test_read_dbt_manifest_():
    result = read_dbt_manifest(dbt_manifest)
    assert len([node for node in result["nodes"].values() if node.get("resource_type") == "model"]) == 5


def test_cli():
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "import",
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
            "dbt",
            "--source",
            dbt_manifest,
            "--model",
            "customers",
            "--model",
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


# --- Versioned model filter tests ---


def test_import_versioned_dbt_manifest_unversioned_filter_returns_all_versions():
    """A plain model name (no .vN suffix) should import every version of that model."""
    result = DataContract.import_from_source("dbt", dbt_manifest_versioned, dbt_model=["mart_orders"])

    schema_names = [s.name for s in result.schema_]
    assert "mart_orders" in schema_names
    assert len([s for s in result.schema_ if s.name == "mart_orders"]) == 2, (
        "Expected both v1 and v2 of mart_orders to be imported"
    )


def test_import_versioned_dbt_manifest_v1_filter():
    """--model mart_orders.v1 should import only the v1 model, not v2."""
    result = DataContract.import_from_source("dbt", dbt_manifest_versioned, dbt_model=["mart_orders.v1"])

    assert result.schema_, "Expected at least one schema but got an empty contract"
    assert len(result.schema_) == 1, f"Expected exactly 1 schema, got {len(result.schema_)}"
    assert result.schema_[0].name == "mart_orders"
    # v1 has 2 columns; v2 has 3 (adds 'currency')
    field_names = [p.name for p in result.schema_[0].properties]
    assert "currency" not in field_names, "currency is a v2-only column; v1 should not contain it"


def test_import_versioned_dbt_manifest_v2_filter():
    """--model mart_orders.v2 should import only the v2 model, not v1."""
    result = DataContract.import_from_source("dbt", dbt_manifest_versioned, dbt_model=["mart_orders.v2"])

    assert result.schema_, "Expected at least one schema but got an empty contract"
    assert len(result.schema_) == 1, f"Expected exactly 1 schema, got {len(result.schema_)}"
    assert result.schema_[0].name == "mart_orders"
    field_names = [p.name for p in result.schema_[0].properties]
    assert "currency" in field_names, "currency is a v2-only column and should be present"


def test_cli_versioned_filter_v1():
    """CLI: --model mart_orders.v1 should exit 0 and produce non-empty output."""
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "import",
            "dbt",
            "--source",
            dbt_manifest_versioned,
            "--model",
            "mart_orders.v1",
        ],
    )
    assert result.exit_code == 0
    parsed = yaml.safe_load(result.output)
    assert parsed.get("schema"), "Expected non-empty schema in CLI output for mart_orders.v1"
