import yaml
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract


def test_cli():
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["export", "./fixtures/osi/export/odcs.yaml", "--format", "osi"],
    )
    assert result.exit_code == 0


def test_export_osi_semantic_model():
    data_contract = DataContract(data_contract_file="fixtures/osi/export/odcs.yaml")
    result = data_contract.export("osi")

    with open("fixtures/osi/export/expected_osi.yaml") as f:
        expected = f.read()

    print("Result:\n", result)
    assert yaml.safe_load(result) == yaml.safe_load(expected)


def test_export_osi_relationships():
    """Test that references are exported as relationships."""
    data_contract = DataContract(data_contract_file="fixtures/osi/export/odcs.yaml")
    result = data_contract.export("osi")

    osi_model = yaml.safe_load(result)
    model = osi_model["semantic_model"]

    # Verify relationships exist
    assert "relationships" in model
    assert len(model["relationships"]) >= 1

    # Verify orders->customers relationship
    rel = next(
        (r for r in model["relationships"] if r["from"] == "orders" and r["to"] == "customers"),
        None,
    )
    assert rel is not None
    assert rel["from_columns"] == ["customer_id"]
    assert rel["to_columns"] == ["customer_id"]


def test_export_osi_time_dimensions():
    """Test that date/timestamp fields get dimension.is_time=true."""
    data_contract = DataContract(data_contract_file="fixtures/osi/export/odcs.yaml")
    result = data_contract.export("osi")

    osi_model = yaml.safe_load(result)
    orders = next(d for d in osi_model["semantic_model"]["datasets"] if d["name"] == "orders")

    order_date_field = next(f for f in orders["fields"] if f["name"] == "order_date")
    assert "dimension" in order_date_field
    assert order_date_field["dimension"]["is_time"] is True


def test_export_osi_expressions():
    """Test that fields have proper ANSI_SQL expressions."""
    data_contract = DataContract(data_contract_file="fixtures/osi/export/odcs.yaml")
    result = data_contract.export("osi")

    osi_model = yaml.safe_load(result)
    orders = next(d for d in osi_model["semantic_model"]["datasets"] if d["name"] == "orders")

    for field in orders["fields"]:
        assert "expression" in field
        assert "dialects" in field["expression"]
        dialect = field["expression"]["dialects"][0]
        assert dialect["dialect"] == "ANSI_SQL"
        assert "expression" in dialect


def test_roundtrip_osi():
    """Test that import -> export produces valid OSI."""
    # Import OSI
    imported_odcs = DataContract.import_from_source("osi", "fixtures/osi/import/orders_semantic_model.yaml")

    # Wrap in DataContract to export
    dc = DataContract(data_contract=imported_odcs)
    exported = dc.export("osi")
    osi_model = yaml.safe_load(exported)

    # Verify structure is valid
    assert "semantic_model" in osi_model
    model = osi_model["semantic_model"]
    assert "name" in model
    assert "datasets" in model
    assert len(model["datasets"]) == 2
