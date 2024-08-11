import os

import pytest
from dotenv import load_dotenv

from datacontract.data_contract import DataContract

datacontract = "fixtures/gcs-json-remote/datacontract.yaml"
load_dotenv(override=True)


@pytest.mark.skipif(
    os.environ.get("DATACONTRACT_GCS_KEY_ID") is None or os.environ.get("DATACONTRACT_GCS_SECRET") is None,
    reason="Requires DATACONTRACT_GCS_KEY_ID, and DATACONTRACT_GCS_SECRET to be set",
)
def test_test_gcs_json_remote_gcs_url():
    """
    server.type "gcs" and gs:// locations work with DuckDB, but are not yet supported for json schema testing
    """
    data_contract = DataContract(
        data_contract_file=datacontract,
        server="gcs-url",
    )

    run = data_contract.test()

    print(run)
    assert run.result == "passed"


@pytest.mark.skipif(
    os.environ.get("DATACONTRACT_GCS_KEY_ID") is None or os.environ.get("DATACONTRACT_GCS_SECRET") is None,
    reason="Requires DATACONTRACT_GCS_KEY_ID, and DATACONTRACT_GCS_SECRET to be set",
)
def test_test_gcs_json_remote_s3_style(monkeypatch):
    monkeypatch.setenv("DATACONTRACT_S3_ACCESS_KEY_ID", os.environ.get("DATACONTRACT_GCS_KEY_ID"))
    monkeypatch.setenv("DATACONTRACT_S3_SECRET_ACCESS_KEY", os.environ.get("DATACONTRACT_GCS_SECRET"))

    data_contract = DataContract(
        data_contract_file=datacontract,
        server="s3-style",
    )

    run = data_contract.test()

    print(run)
    assert run.result == "passed"
    assert all(check.result == "passed" for check in run.checks)
