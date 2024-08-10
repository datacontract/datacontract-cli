import os

import pytest
from testcontainers.minio import MinioContainer

from datacontract.data_contract import DataContract

datacontract = "./fixtures/s3-json-multiple-models/datacontract.yaml"
data_directory = "./fixtures/s3-json-multiple-models/data/"
bucket_name = "multiple-bucket"
s3_access_key = "test-access"
s3_secret_access_key = "test-secret"

# logging.basicConfig(level=logging.INFO, force=True)


@pytest.fixture(scope="session")
def minio_container():
    with MinioContainer(
        image="quay.io/minio/minio", access_key=s3_access_key, secret_key=s3_secret_access_key
    ) as minio_container:
        yield minio_container


def test_test_s3_json(minio_container, monkeypatch):
    monkeypatch.setenv("DATACONTRACT_S3_ACCESS_KEY_ID", "test-access")
    monkeypatch.setenv("DATACONTRACT_S3_SECRET_ACCESS_KEY", "test-secret")

    data_contract_str = _prepare_s3_files(minio_container)

    data_contract = DataContract(data_contract_str=data_contract_str)

    run = data_contract.test()

    print(run.pretty())
    assert run.result == "passed"
    assert all(check.result == "passed" for check in run.checks)


def _prepare_s3_files(minio_container):
    s3_endpoint_url = f"http://{minio_container.get_container_host_ip()}:{minio_container.get_exposed_port(9000)}"
    minio_client = minio_container.get_client()
    minio_client.make_bucket(bucket_name)

    for root, dirs, files in os.walk(data_directory):
        for filename in files:
            file_path = os.path.join(root, filename)
            object_name = os.path.relpath(file_path)
            with open(file_path, "rb") as file_data:
                file_stat = os.stat(file_path)
                minio_client.put_object(bucket_name, object_name, file_data, file_stat.st_size)
    with open(datacontract) as data_contract_file:
        data_contract_str = data_contract_file.read()
    data_contract_str = data_contract_str.replace("__S3_ENDPOINT_URL__", s3_endpoint_url)
    return data_contract_str
