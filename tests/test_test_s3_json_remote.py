from datacontract.data_contract import DataContract

# logging.basicConfig(level=logging.INFO, force=True)

datacontract = "fixtures/s3-json-remote/datacontract.yaml"


def test_test_s3_json(monkeypatch):
    monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("AWS_SECRET_ACCESS_KEY", raising=False)
    monkeypatch.delenv("DATACONTRACT_S3_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("DATACONTRACT_S3_SECRET_ACCESS_KEY", raising=False)

    data_contract = DataContract(data_contract_file=datacontract)

    run = data_contract.test()

    print(run)
    assert run.result == "passed"
    assert all(check.result == "passed" for check in run.checks)
