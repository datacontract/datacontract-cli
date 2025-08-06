import logging
import os

import pytest
from dotenv import load_dotenv

from datacontract.data_contract import DataContract

logging.basicConfig(level=logging.INFO, force=True)
load_dotenv(override=True)
datacontract = "fixtures/athena-iceberg/iceberg_example.odcs.yaml"


@pytest.mark.skipif(
    os.environ.get("DATACONTRACT_S3_ACCESS_KEY_ID") is None
    or os.environ.get("DATACONTRACT_S3_SECRET_ACCESS_KEY") is None,
    reason="Requires DATACONTRACT_S3_ACCESS_KEY_ID, and DATACONTRACT_S3_SECRET_ACCESS_KEY to be set",
)
def test_test_athena_iceberg(monkeypatch):
    data_contract = DataContract(data_contract_file=datacontract)

    run = data_contract.test()

    print(run.pretty())
    assert run.result == "passed"
    assert all(check.result == "passed" for check in run.checks)
