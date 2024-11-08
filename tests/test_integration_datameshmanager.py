import os

import pytest
from dotenv import load_dotenv
from typer.testing import CliRunner

from datacontract.data_contract import DataContract

runner = CliRunner()
load_dotenv(override=True)


@pytest.mark.skipif(
    os.environ.get("DATAMESH_MANAGER_API_KEY") is None, reason="Requires DATAMESH_MANAGER_API_KEY to be set"
)
def test_remote_data_contract():
    data_contract = DataContract(
        data_contract_file="https://app.datamesh-manager.com/checker1/datacontracts/verbraucherpreisindex-61111-0002zzz",
        publish_url="https://api.datamesh-manager.com/api/test-results",
    )

    run = data_contract.test()

    print(run)
    assert run.result == "passed"
    assert len(run.checks) == 4
    assert all(check.result == "passed" for check in run.checks)
