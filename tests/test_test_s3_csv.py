import os

import pytest
from testcontainers.minio import MinioContainer

from datacontract.data_contract import DataContract

# logging.basicConfig(level=logging.DEBUG, force=True)

datacontract = "fixtures/s3-csv/datacontract.yaml"
file_name = "fixtures/s3-csv/data/sample_data.csv"
bucket_name = "test-bucket"
s3_access_key = "test-access"
s3_secret_access_key = "test-secret"


@pytest.fixture(scope="session")
def minio_container():
    with MinioContainer(
        image="quay.io/minio/minio", access_key=s3_access_key, secret_key=s3_secret_access_key
    ) as minio_container:
        yield minio_container


def test_test_s3_csv(minio_container, monkeypatch):
    monkeypatch.setenv("DATACONTRACT_S3_ACCESS_KEY_ID", s3_access_key)
    monkeypatch.setenv("DATACONTRACT_S3_SECRET_ACCESS_KEY", s3_secret_access_key)
    data_contract_str = _prepare_s3_files(minio_container)
    data_contract = DataContract(data_contract_str=data_contract_str)

    run = data_contract.test()

    print(run)
    assert run.result == "passed"
    assert all(check.result == "passed" for check in run.checks)


def _prepare_s3_files(minio_container):
    s3_endpoint_url = f"http://{minio_container.get_container_host_ip()}:{minio_container.get_exposed_port(9000)}"
    minio_client = minio_container.get_client()
    minio_client.make_bucket(bucket_name)
    with open(file_name, "rb") as file:
        minio_client.put_object(bucket_name, file_name, file, os.path.getsize(file_name))
    with open(datacontract) as data_contract_file:
        data_contract_str = data_contract_file.read()
    data_contract_str = data_contract_str.replace("__S3_ENDPOINT_URL__", s3_endpoint_url)
    return data_contract_str
