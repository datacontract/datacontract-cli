from pathlib import Path

import pytest
import yaml
from testcontainers.minio import MinioContainer

from datacontract.data_contract import DataContract

CONTRACT = "fixtures/xlsx/datacontract.yaml"
WORKBOOK = "fixtures/xlsx/delivery.xlsx"
bucket_name = "test-bucket"
s3_access_key = "test-access"
s3_secret_access_key = "test-secret"


@pytest.fixture(scope="session")
def minio_container():
    with MinioContainer(
        image="cgr.dev/chainguard/minio", access_key=s3_access_key, secret_key=s3_secret_access_key
    ) as minio_container:
        yield minio_container


def test_test_s3_xlsx(minio_container, monkeypatch):
    monkeypatch.setenv("DATACONTRACT_S3_ACCESS_KEY_ID", s3_access_key)
    monkeypatch.setenv("DATACONTRACT_S3_SECRET_ACCESS_KEY", s3_secret_access_key)
    minio_container.get_client().make_bucket(bucket_name)
    minio_container.get_client().fput_object(bucket_name, "delivery.xlsx", WORKBOOK)
    data = yaml.safe_load(Path(CONTRACT).read_text())
    data["servers"] = [
        {
            "server": "s3",
            "type": "s3",
            "location": f"s3://{bucket_name}/delivery.xlsx",
            "endpointUrl": f"http://{minio_container.get_container_host_ip()}:{minio_container.get_exposed_port(9000)}",
            "format": "xlsx",
        }
    ]

    run = DataContract(data_contract_str=yaml.safe_dump(data)).test()

    assert run.result == "passed", [(c.name, c.reason) for c in run.checks if c.result != "passed"]
    assert {"Orders", "Country Codes"} <= {check.model for check in run.checks}
