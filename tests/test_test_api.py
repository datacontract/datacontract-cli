import logging

from datacontract.data_contract import DataContract

logging.basicConfig(level=logging.DEBUG, force=True)


datacontract = "fixtures/api/weather-service.odcs.yaml"


def test_test_api(monkeypatch):
    with open(datacontract) as data_contract_file:
        data_contract_str = data_contract_file.read()
    data_contract = DataContract(data_contract_str=data_contract_str)

    run = data_contract.test()

    print(run)
    assert run.result == "passed"
    assert all(check.result == "passed" for check in run.checks)


# TODO mock
