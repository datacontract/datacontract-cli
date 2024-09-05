from typer.testing import CliRunner

from datacontract.data_contract import DataContract
from datacontract.model.data_contract_specification import Field

runner = CliRunner()

# logging.basicConfig(level=logging.DEBUG, force=True)


def test_aliases():
    data_contract = DataContract(data_contract_file="fixtures/spec/datacontract_fields_field.yaml")
    spec = data_contract.get_data_contract_specification()
    model_field = spec.models["sample_model"].fields["id"]
    definition_field = model_field.fields["id"]
    assert isinstance(model_field, Field)
    assert isinstance(definition_field, Field)
