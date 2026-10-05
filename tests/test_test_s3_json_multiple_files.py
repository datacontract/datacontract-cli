import os
from types import SimpleNamespace

import fastjsonschema
import pytest
from testcontainers.minio import MinioContainer

from datacontract.config import Config
from datacontract.data_contract import DataContract
from datacontract.engines.fastjsonschema import check_jsonschema
from datacontract.model.exceptions import DataContractException
from datacontract.model.run import Run

datacontract = "fixtures/s3-json-multiple-files/datacontract.yaml"
data_directory = "fixtures/s3-json-multiple-files/data/"
bucket_name = "multiple-files-bucket"
s3_access_key = "test-access"
s3_secret_access_key = "test-secret"


@pytest.fixture(scope="session")
def minio_container():
    with MinioContainer(
        image="cgr.dev/chainguard/minio", access_key=s3_access_key, secret_key=s3_secret_access_key
    ) as minio_container:
        yield minio_container


def test_test_s3_json_validates_every_file(minio_container, monkeypatch):
    # The invalid record is in orders-1.json, and orders-2.json is valid:
    # the jsonschema check must fail even though the last file matched by the glob is valid.
    monkeypatch.setenv("DATACONTRACT_S3_ACCESS_KEY_ID", s3_access_key)
    monkeypatch.setenv("DATACONTRACT_S3_SECRET_ACCESS_KEY", s3_secret_access_key)
    data_contract_str = _prepare_s3_files(minio_container)
    data_contract = DataContract(data_contract_str=data_contract_str)

    run = data_contract.test()

    print(run.pretty())
    assert run.result == "failed"
    assert any(check.engine == "jsonschema" and check.result == "failed" for check in run.checks)


def test_test_s3_json_stops_reading_files_at_error_limit(monkeypatch):
    read_files = []

    def fake_yield_s3_files(s3_endpoint_url, s3_location, config=None):
        for file_name in ["orders-1.json", "orders-2.json"]:
            read_files.append(file_name)
            yield '{"order_id": "1001", "order_total": "not-a-number"}'

    monkeypatch.setattr(check_jsonschema, "yield_s3_files", fake_yield_s3_files)
    schema = {"type": "object", "properties": {"order_total": {"type": "integer"}}}
    server = SimpleNamespace(endpointUrl=None, location="s3://bucket/*.json", delimiter="new_line")

    run = Run.create_run()

    failed = check_jsonschema.process_s3_file(
        run, server, schema, "orders", fastjsonschema.compile(schema), Config(max_errors=1)
    )

    assert failed
    assert [check.result for check in run.checks] == ["failed"]
    assert read_files == ["orders-1.json"]


@pytest.mark.parametrize("max_errors", [0, -1])
def test_resolve_error_limit_rejects_non_positive_values(max_errors):
    with pytest.raises(DataContractException, match="DATACONTRACT_MAX_ERRORS must be at least 1"):
        check_jsonschema.resolve_error_limit(Config(max_errors=max_errors))


def _prepare_s3_files(minio_container):
    s3_endpoint_url = f"http://{minio_container.get_container_host_ip()}:{minio_container.get_exposed_port(9000)}"
    minio_client = minio_container.get_client()
    minio_client.make_bucket(bucket_name)

    for filename in os.listdir(data_directory):
        file_path = data_directory + filename
        with open(file_path, "rb") as file_data:
            minio_client.put_object(bucket_name, file_path, file_data, os.path.getsize(file_path))
    with open(datacontract) as data_contract_file:
        data_contract_str = data_contract_file.read()
    return data_contract_str.replace("__S3_ENDPOINT_URL__", s3_endpoint_url)
