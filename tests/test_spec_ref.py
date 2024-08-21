from typer.testing import CliRunner

from datacontract.data_contract import DataContract

runner = CliRunner()

# logging.basicConfig(level=logging.DEBUG, force=True)


def test_aliases():
    data_contract = DataContract(data_contract_file="fixtures/spec/datacontract_aliases.yaml", examples=True)
    spec = data_contract.get_data_contract_specification()
    yaml = spec.to_yaml()
    print(yaml)
    assert "$ref" in yaml
