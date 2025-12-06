from typer.testing import CliRunner

from datacontract.data_contract import DataContract
from open_data_contract_standard.model import SchemaProperty

runner = CliRunner()

# logging.basicConfig(level=logging.DEBUG, force=True)


def test_nested_properties():
    """Test that nested properties in ODCS schema are properly parsed."""
    data_contract = DataContract(data_contract_file="fixtures/spec/datacontract_nested_properties.odcs.yaml")
    spec = data_contract.get_data_contract()

    # Find the sample_model schema
    sample_schema = next((s for s in spec.schema_ if s.name == "sample_model"), None)
    assert sample_schema is not None

    # Find the id property
    id_property = next((p for p in sample_schema.properties if p.name == "id"), None)
    assert id_property is not None
    assert isinstance(id_property, SchemaProperty)

    # Check nested properties if they exist
    if id_property.properties:
        nested_property = next((p for p in id_property.properties if p.name == "nested_id"), None)
        assert nested_property is not None
        assert isinstance(nested_property, SchemaProperty)
