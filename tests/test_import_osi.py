import yaml
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract


def test_cli():
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "import",
            "--format",
            "osi",
            "--source",
            "fixtures/osi/import/orders_semantic_model.yaml",
        ],
    )
    assert result.exit_code == 0


def test_import_osi_semantic_model():
    result = DataContract.import_from_source("osi", "fixtures/osi/import/orders_semantic_model.yaml")

    with open("fixtures/osi/import/expected_odcs.yaml") as f:
        expected = f.read()

    print("Result:\n", result.to_yaml())
    assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected)


def test_import_osi_with_metrics():
    """Test that metrics are preserved in custom properties."""
    result = DataContract.import_from_source("osi", "fixtures/osi/import/orders_semantic_model.yaml")

    # Metrics should be stored in customProperties at contract level or as special schema
    yaml_output = result.to_yaml()
    assert "total_revenue" in yaml_output or "metrics" in yaml_output


def test_import_osi_relationships():
    """Test that relationships are properly imported."""
    result = DataContract.import_from_source("osi", "fixtures/osi/import/orders_semantic_model.yaml")

    orders_schema = next(s for s in result.schema_ if s.name == "orders")
    customer_id = next(p for p in orders_schema.properties if p.name == "customer_id")

    # Relationship should be converted to relationships list
    assert customer_id.relationships is not None
    assert len(customer_id.relationships) == 1
    assert customer_id.relationships[0].to == "customers.customer_id"


def test_import_osi_simple():
    """Test importing a simple OSI model without relationships or metrics."""
    result = DataContract.import_from_source("osi", "fixtures/osi/import/simple_model.yaml")

    assert result.name == "simple_model"
    assert len(result.schema_) == 1

    users_schema = result.schema_[0]
    assert users_schema.name == "users"
    assert users_schema.physicalName == "public.users"
    assert len(users_schema.properties) == 3

    id_prop = next(p for p in users_schema.properties if p.name == "id")
    assert id_prop.primaryKey is True
