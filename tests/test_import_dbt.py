import yaml
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract
from datacontract.imports.dbt_importer import import_dbt_manifest, read_dbt_manifest

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


def test_import_dbt_manifest_preserves_meta_classification():
    manifest = {
        "metadata": {
            "dbt_schema_version": "https://schemas.getdbt.com/dbt/manifest/v12.json",
            "dbt_version": "1.8.0",
            "project_name": "test_project",
            "adapter_type": "databricks",
        },
        "nodes": {
            "model.test_project.fact_workers": {
                "resource_type": "model",
                "unique_id": "model.test_project.fact_workers",
                "name": "fact_workers",
                "description": "Test model",
                "config": {"materialized": "table"},
                "tags": [],
                "columns": {
                    "employee_id": {
                        "name": "employee_id",
                        "data_type": "string",
                        "description": "Employee identifier",
                        "constraints": [{"type": "not_null"}, {"type": "unique"}],
                        "meta": {"classification": "C2"},
                        "tags": [],
                    },
                    "nationality": {
                        "name": "nationality",
                        "data_type": "string",
                        "description": "Nationality of the worker",
                        "constraints": [],
                        "meta": {"classification": "C2"},
                        "tags": ["classification:C2"],
                    },
                },
            }
        },
        "child_map": {"model.test_project.fact_workers": []},
    }

    contract = import_dbt_manifest(manifest, [], ["model"])
    employee_id = contract.schema_[0].properties[0]
    nationality = contract.schema_[0].properties[1]

    assert employee_id.classification == "C2"

    assert nationality.classification == "C2"
    assert nationality.customProperties is not None
    assert any(cp.property == "tags" and cp.value == "classification:C2" for cp in nationality.customProperties)


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


def test_import_dbt_manifest_id_from_project_name():
    """The contract id comes from the dbt project, not the placeholder default."""
    odcs = import_dbt_manifest(read_dbt_manifest(dbt_manifest), [], ["model"])

    assert odcs.id == "jaffle_shop"
    assert odcs.id != "my-data-contract"

    versioned = import_dbt_manifest(read_dbt_manifest(dbt_manifest_versioned), [], ["model"])
    assert versioned.id == "test_project"


def test_import_dbt_manifest_id_is_slugified():
    """A project name with spaces or capitals is normalised, as in the Power BI importer."""
    odcs = import_dbt_manifest({"metadata": {"project_name": "My Jaffle Shop"}, "nodes": {}}, [], ["model"])

    assert odcs.id == "my-jaffle-shop"
    assert odcs.name == "My Jaffle Shop"


def test_import_dbt_manifest_id_falls_back_without_project_name():
    """A manifest with no project_name keeps the previous default id."""
    odcs = import_dbt_manifest({"metadata": {}, "nodes": {}}, [], ["model"])

    assert odcs.id == "my-data-contract"


def test_map_dbt_type_to_odcs_temporal_types():
    from datacontract.imports.dbt_importer import map_dbt_type_to_odcs

    assert map_dbt_type_to_odcs("timestamp") == "timestamp"
    assert map_dbt_type_to_odcs("TIMESTAMP_NTZ(9)") == "timestamp"
    assert map_dbt_type_to_odcs("datetime") == "timestamp"
    assert map_dbt_type_to_odcs("date") == "date"
    assert map_dbt_type_to_odcs("time") == "time"
