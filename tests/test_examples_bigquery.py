import logging
import os

import pytest

from datacontract.data_contract import DataContract

logging.basicConfig(level=logging.INFO, force=True)

datacontract = "examples/bigquery/datacontract.yaml"


# Deactivated because the test requires special setup on a non-free BigQuery account.
# Can activate for testing locally, using a custom account_info file.
# For the provided datacontract.yaml the data file from s3-csv should be imported in the target BigQuery table.
@pytest.mark.skipif(os.environ.get("DATACONTRACT_BIGQUERY_ACCOUNT_INFO_JSON_PATH") is None,
                    reason="Requires DATACONTRACT_BIGQUERY_ACCOUNT_INFO_JSON_PATH to be set")
def _test_examples_bigquery():
    data_contract = DataContract(data_contract_file=datacontract)

    run = data_contract.test()

    print(run)
    assert run.result == "passed"
    assert all(check.result == "passed" for check in run.checks)
