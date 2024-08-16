import os

import pytest
from dotenv import load_dotenv

from datacontract.data_contract import DataContract

# logging.basicConfig(level=logging.DEBUG, force=True)

datacontract = "fixtures/databricks-sql/datacontract.yaml"

load_dotenv(override=True)


@pytest.mark.skipif(
    os.environ.get("DATACONTRACT_DATABRICKS_TOKEN") is None, reason="Requires DATACONTRACT_DATABRICKS_TOKEN to be set"
)
def _test_test_databricks_sql():
    # os.environ['DATACONTRACT_DATABRICKS_TOKEN'] = "xxx"
    # os.environ['DATACONTRACT_DATABRICKS_HTTP_PATH'] = "/sql/1.0/warehouses/b053a326fa014fb3"
    data_contract = DataContract(data_contract_file=datacontract)

    run = data_contract.test()

    print(run)
    assert run.result == "passed"
    assert all(check.result == "passed" for check in run.checks)
