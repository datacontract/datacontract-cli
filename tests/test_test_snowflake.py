import os

import pytest
from dotenv import load_dotenv

from datacontract.data_contract import DataContract
from tests.dcs_deprecation import assert_dcs_deprecation_is_the_only_warning, without_dcs_deprecation

# logging.basicConfig(level=logging.INFO, force=True)
load_dotenv(override=True)

datacontract = "fixtures/snowflake/datacontract.yaml"


@pytest.mark.skipif(
    os.environ.get("DATACONTRACT_SNOWFLAKE_USERNAME") is None,
    reason="Requires DATACONTRACT_SNOWFLAKE_USERNAME to be set",
)
def test_test_snowflake():
    # os.environ['DATACONTRACT_SNOWFLAKE_USERNAME'] = "xxx"
    # os.environ['DATACONTRACT_SNOWFLAKE_PASSWORD'] = "xxx"
    # os.environ['DATACONTRACT_SNOWFLAKE_ROLE'] = "xxx"
    # os.environ['DATACONTRACT_SNOWFLAKE_WAREHOUSE'] = "COMPUTE_WH"
    data_contract = DataContract(data_contract_file=datacontract)

    run = data_contract.test()

    print(run)
    assert_dcs_deprecation_is_the_only_warning(run)
    assert all(check.result == "passed" for check in without_dcs_deprecation(run))
