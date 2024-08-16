import os

import pytest
from dotenv import load_dotenv

from datacontract.data_contract import DataContract

# logging.basicConfig(level=logging.INFO, force=True)

load_dotenv(override=True)


@pytest.mark.skipif(
    os.environ.get("DATACONTRACT_AZURE_TENANT_ID") is None
    or os.environ.get("DATACONTRACT_AZURE_CLIENT_ID") is None
    or os.environ.get("DATACONTRACT_AZURE_CLIENT_SECRET") is None,
    reason="Requires DATACONTRACT_AZURE_TENANT_ID, DATACONTRACT_AZURE_CLIENT_ID, and DATACONTRACT_AZURE_CLIENT_SECRET to be set",
)
def test_test_azure_parquet_remote():
    data_contract = DataContract(data_contract_file="fixtures/azure-parquet-remote/datacontract.yaml")

    run = data_contract.test()

    print(run)
    assert run.result == "passed"


@pytest.mark.skipif(
    os.environ.get("DATACONTRACT_AZURE_TENANT_ID") is None
    or os.environ.get("DATACONTRACT_AZURE_CLIENT_ID") is None
    or os.environ.get("DATACONTRACT_AZURE_CLIENT_SECRET") is None,
    reason="Requires DATACONTRACT_AZURE_TENANT_ID, DATACONTRACT_AZURE_CLIENT_ID, and DATACONTRACT_AZURE_CLIENT_SECRET to be set",
)
def test_test_azure_json_remote():
    data_contract = DataContract(data_contract_file="fixtures/azure-json-remote/datacontract.yaml")

    run = data_contract.test()

    print(run.pretty())
    assert run.result == "passed"
