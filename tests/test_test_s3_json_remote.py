import os

import pytest

from datacontract.data_contract import DataContract

# logging.basicConfig(level=logging.INFO, force=True)

datacontract = "fixtures/s3-json-remote/datacontract.yaml"


# Disabled, as this test fails when another local s3 test runs, not clear why.
# Maybe with env variables or the DuckDB connection...
def _test_test_s3_json():
    if "AWS_ACCESS_KEY_ID" in os.environ:
        pytest.fail("Failed: AWS_ACCESS_KEY_ID is set, which you break this test")
    if "AWS_SECRET_ACCESS_KEY" in os.environ:
        pytest.fail("Failed: AWS_SECRET_ACCESS_KEY is set, which you break this test")
    if "DATACONTRACT_S3_ACCESS_KEY_ID" in os.environ:
        pytest.fail("Failed: DATACONTRACT_S3_ACCESS_KEY_ID is set, which you break this test")
    if "DATACONTRACT_S3_SECRET_ACCESS_KEY" in os.environ:
        pytest.fail("Failed: DATACONTRACT_S3_SECRET_ACCESS_KEY is set, which you break this test")
    data_contract = DataContract(data_contract_file=datacontract)

    # Get all environment variables as a dictionary
    env_vars = os.environ

    # Print each environment variable
    for key, value in env_vars.items():
        print(f"{key}: {value}")

    run = data_contract.test()

    print(run)
    assert run.result == "passed"
    assert all(check.result == "passed" for check in run.checks)
