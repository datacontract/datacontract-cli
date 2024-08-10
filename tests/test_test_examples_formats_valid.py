from typer.testing import CliRunner

from datacontract.data_contract import DataContract

runner = CliRunner()

# logging.basicConfig(level=logging.DEBUG, force=True)


def test_formats():
    data_contract = DataContract(data_contract_file="fixtures/examples/datacontract_formats_valid.yaml", examples=True)
    run = data_contract.test()
    print(run)
    print(run.result)
    assert run.result == "passed"
