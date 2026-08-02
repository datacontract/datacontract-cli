import os

import pytest
from dotenv import load_dotenv

from datacontract.data_contract import DataContract

# logging.basicConfig(level=logging.DEBUG, force=True)

datacontract = "fixtures/databricks-sql/datacontract.yaml"

load_dotenv(override=True)


def test_connect_skips_memtable_volume_creation():
    # ibis's Databricks backend runs CREATE VOLUME at connect time for memtable
    # staging; tests never use memtables and a read-only principal may not be
    # allowed to create volumes, so the connect helper must suppress it.
    from ibis.backends.databricks import Backend

    from datacontract.engines.ibis.connections.connect import _databricks_connect

    original = Backend._post_connect
    seen = {}

    class StubDatabricks:
        @staticmethod
        def connect(**kwargs):
            seen["post_connect"] = Backend._post_connect
            return "connection"

    class StubIbis:
        databricks = StubDatabricks()

    assert _databricks_connect(StubIbis(), server_hostname="example") == "connection"
    assert seen["post_connect"] is not original
    assert seen["post_connect"](object(), memtable_volume="unused") is None
    assert Backend._post_connect is original


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
