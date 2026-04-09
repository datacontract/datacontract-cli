from datacontract.data_contract import DataContract

V1 = "fixtures/changelog/integration/changelog_integration_v1.yaml"


def test_get_data_contract_file_returns_path():
    dc = DataContract(data_contract_file=V1)
    assert dc.get_data_contract_file() == V1


def test_get_data_contract_file_returns_none_when_not_set():
    dc = DataContract(
        data_contract_str="dataContractSpecification: 1.1.0\nid: test\ninfo:\n  title: t\n  version: 1.0.0\n"
    )
    assert dc.get_data_contract_file() is None
