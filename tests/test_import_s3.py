"""Tests for the S3 importer.

The format detection and schema naming are pure and tested directly; the read
itself runs against a MinIO container, the same seam the s3 test suites use.
"""

import os

import pytest
from testcontainers.minio import MinioContainer

from datacontract.data_contract import DataContract
from datacontract.imports.s3_importer import detect_format, schema_name
from datacontract.model.exceptions import DataContractException
from datacontract.model.run import ResultEnum

BUCKET = "test-bucket"
ACCESS_KEY = "test-access"
SECRET_KEY = "test-secret"
CSV_FIXTURE = "fixtures/s3-csv/data/sample_data.csv"


@pytest.mark.parametrize(
    "location, expected",
    [
        ("s3://bucket/orders/orders.json", "json"),
        ("s3://bucket/orders/orders.ndjson", "json"),
        ("s3://bucket/orders/orders.JSONL", "json"),
        ("s3://bucket/orders/orders.csv", "csv"),
        ("s3://bucket/orders/*.parquet", "parquet"),
        ("s3://bucket/orders/", None),  # a delta table has no suffix
    ],
)
def test_detect_format(location, expected):
    assert detect_format(location) == expected


@pytest.mark.parametrize(
    "location, expected",
    [
        ("s3://bucket/orders/orders.csv", "orders"),
        ("s3://bucket/orders/*.json", "orders"),
        ("s3://bucket/orders/orders-2024-01.json", "orders_2024_01"),
        ("s3://bucket/orders/", "orders"),
    ],
)
def test_schema_name(location, expected):
    assert schema_name(location) == expected


def test_an_unknown_format_is_rejected_with_the_options():
    with pytest.raises(DataContractException) as exc_info:
        DataContract.import_from_source("s3", "s3://bucket/orders/")

    assert "--format" in exc_info.value.reason
    assert "parquet" in exc_info.value.reason


def test_a_missing_location_is_rejected():
    with pytest.raises(DataContractException) as exc_info:
        DataContract.import_from_source("s3", None)

    assert "location is required" in exc_info.value.reason


@pytest.fixture(scope="module")
def minio(request):
    with MinioContainer(image="quay.io/minio/minio", access_key=ACCESS_KEY, secret_key=SECRET_KEY) as container:
        client = container.get_client()
        client.make_bucket(BUCKET)
        with open(CSV_FIXTURE, "rb") as file:
            client.put_object(BUCKET, "orders/orders.csv", file, os.path.getsize(CSV_FIXTURE))
        yield container


@pytest.fixture
def credentials(monkeypatch):
    monkeypatch.setenv("DATACONTRACT_S3_ACCESS_KEY_ID", ACCESS_KEY)
    monkeypatch.setenv("DATACONTRACT_S3_SECRET_ACCESS_KEY", SECRET_KEY)


def _endpoint(minio):
    return f"http://{minio.get_container_host_ip()}:{minio.get_exposed_port(9000)}"


def test_import_s3_csv(minio, credentials):
    result = DataContract.import_from_source("s3", f"s3://{BUCKET}/orders/orders.csv", endpoint_url=_endpoint(minio))

    server = result.servers[0]
    assert (server.type, server.format) == ("s3", "csv")
    assert server.location == f"s3://{BUCKET}/orders/orders.csv"
    assert result.schema_[0].name == "orders"
    assert [prop.name for prop in result.schema_[0].properties]


def test_imported_contract_passes_test_without_editing(minio, credentials):
    """The point of the importer: import, then test, no hand-editing."""
    result = DataContract.import_from_source("s3", f"s3://{BUCKET}/orders/orders.csv", endpoint_url=_endpoint(minio))

    run = DataContract(data_contract_str=result.to_yaml()).test()

    print(run.pretty())
    assert run.result == ResultEnum.passed


def test_import_s3_produces_a_valid_contract(minio, credentials):
    result = DataContract.import_from_source("s3", f"s3://{BUCKET}/orders/orders.csv", endpoint_url=_endpoint(minio))

    assert DataContract(data_contract_str=result.to_yaml()).lint().result == ResultEnum.passed


def test_an_unreadable_object_explains_the_location_and_format(minio, credentials):
    with pytest.raises(DataContractException) as exc_info:
        DataContract.import_from_source("s3", f"s3://{BUCKET}/orders/missing.csv", endpoint_url=_endpoint(minio))

    assert "missing.csv" in exc_info.value.reason
    assert "as csv" in exc_info.value.reason
