import os
import glob

import pytest
from testcontainers.minio import MinioContainer

from datacontract.data_contract import DataContract

# logging.basicConfig(level=logging.DEBUG, force=True)

datacontract = "fixtures/s3-delta/datacontract.yaml"
file_name = "fixtures/s3-delta/data/orders.delta"
bucket_name = "test-bucket"
s3_access_key = "test-access"
s3_secret_access_key = "test-secret"


@pytest.fixture(scope="session")
def minio_container():
    with MinioContainer(
        image="quay.io/minio/minio",
        access_key=s3_access_key,
        secret_key=s3_secret_access_key,
    ) as minio_container:
        yield minio_container


@pytest.mark.skipif(
    os.getenv("CI") == "true",
    reason="""
Runs locally on mac, but fails on CI with
<Error><Code>InvalidTokenId</Code><Message>The security token included in the request is invalid</Message><Key>fixtures/s3-delta/data/orders.delta/_delta_log/_last_checkpoint</Key><BucketName>test-bucket</BucketName><Resource>/test-bucket/fixtures/s3-delta/data/orders.delta/_delta_log/_last_checkpoint</Resource></Error>)

Need to investigate why the token is invalid on CI.
""",
)
def test_test_s3_delta(minio_container, monkeypatch):
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

    rel_paths = glob.glob(file_name + "/**", recursive=True)
    for local_file in rel_paths:
        remote_path = local_file
        if os.path.isfile(local_file):
            minio_client.fput_object(bucket_name, remote_path, local_file)

    with open(datacontract) as data_contract_file:
        data_contract_str = data_contract_file.read()
    data_contract_str = data_contract_str.replace("__S3_ENDPOINT_URL__", s3_endpoint_url)
    return data_contract_str
