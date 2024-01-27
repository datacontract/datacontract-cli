import logging
import os

from datacontract.data_contract import DataContract

logging.basicConfig(level=logging.INFO, force=True)

datacontract = "examples/s3-json-remote/datacontract.yaml"


def test_examples_s3_json():
    if 'DATACONTRACT_S3_ACCESS_KEY_ID' in os.environ:
        del os.environ['DATACONTRACT_S3_ACCESS_KEY_ID']
    if 'DATACONTRACT_S3_SECRET_ACCESS_KEY' in os.environ:
        del os.environ['DATACONTRACT_S3_SECRET_ACCESS_KEY']
    data_contract = DataContract(data_contract_file=datacontract)

    run = data_contract.test()

    print(run)
    assert run.result == "passed"
    assert all(check.result == "passed" for check in run.checks)
