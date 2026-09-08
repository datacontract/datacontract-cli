"""Tests for the S3 importer.

The format detection and schema naming are pure and tested directly; the read
itself runs against a MinIO container, the same seam the s3 test suites use.
"""

from pathlib import Path

import pytest
from testcontainers.minio import MinioContainer

from datacontract.data_contract import DataContract
from datacontract.imports.object_storage_importer import detect_format, schema_name
from datacontract.model.exceptions import DataContractException
from datacontract.model.run import ResultEnum

BUCKET = "test-bucket"
ACCESS_KEY = "test-access"
SECRET_KEY = "test-secret"
# resolved from this file: the container fixture is module-scoped and therefore
# runs before conftest chdirs into the test directory
CSV_FIXTURE = Path(__file__).parent / "fixtures" / "s3-csv" / "data" / "sample_data.csv"


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
            client.put_object(BUCKET, "orders/orders.csv", file, CSV_FIXTURE.stat().st_size)
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


# ---------------------------------------------------------------------------
# One importer serves S3, GCS and Azure; it takes the server type from the
# format it was registered under. The GCS and Azure reads need real credentials,
# which is how the existing gcs/azure suites are gated, so only the dispatch is
# checked here.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("storage, server_type", [("s3", "s3"), ("gcs", "s3"), ("adls", "azure")])
def test_each_storage_writes_its_own_server_type(storage, server_type, monkeypatch):
    result = _import_with_stubbed_read(monkeypatch, storage, "s3://bucket/orders/orders.csv")

    # ODCS calls the Azure server type `azure` and has no GCS type at all, so
    # the format name and the server type deliberately differ for adls and gcs
    assert result.servers[0].type == server_type
    assert result.servers[0].format == "csv"


def test_gcs_writes_an_odcs_server_the_cli_can_lint_and_test(monkeypatch):
    """ODCS has no `gcs` server type; GCS is reached as an S3-compatible server."""
    result = _import_with_stubbed_read(monkeypatch, "gcs", "s3://bucket/orders/orders.csv")

    assert result.servers[0].type == "s3"
    assert result.servers[0].endpointUrl == "https://storage.googleapis.com"
    assert DataContract(data_contract_str=result.to_yaml()).lint().result == ResultEnum.passed


def test_gcs_accepts_a_gs_location(monkeypatch):
    """duckdb reads GCS through the S3 endpoint, which needs the s3:// scheme."""
    result = _import_with_stubbed_read(monkeypatch, "gcs", "gs://bucket/orders/orders.csv")

    assert result.servers[0].location == "s3://bucket/orders/orders.csv"


def test_an_explicit_endpoint_url_wins_over_the_gcs_default(monkeypatch):
    result = _import_with_stubbed_read(
        monkeypatch, "gcs", "s3://bucket/orders/orders.csv", endpoint_url="https://minio.example.com"
    )

    assert result.servers[0].endpointUrl == "https://minio.example.com"


def _import_with_stubbed_read(monkeypatch, storage, location, **kwargs):
    """Import without touching object storage — only the server block is of interest."""
    from datacontract.imports import object_storage_importer

    monkeypatch.setattr(object_storage_importer, "_read_columns", lambda *_: [("id", "BIGINT")])
    return DataContract.import_from_source(storage, location, **kwargs)


@pytest.mark.parametrize("storage", ["s3", "gcs", "adls"])
def test_each_storage_names_its_own_location_in_the_error(storage):
    with pytest.raises(DataContractException) as exc_info:
        DataContract.import_from_source(storage, None)

    assert "location is required" in exc_info.value.reason


def test_adls_uses_the_azure_connection_setup(monkeypatch):
    """Each storage must reach duckdb through its own credential setup."""
    from datacontract.imports import object_storage_importer

    calls = []
    for name in ("setup_s3_connection", "setup_azure_connection"):
        # The fake must match the real signature, so a call-shape regression in
        # _read_columns fails here instead of only in the real command.
        monkeypatch.setattr(
            "datacontract.engines.ibis.connections.duckdb_connection." + name,
            lambda con, server, config, _n=name: calls.append(_n),
        )
    monkeypatch.setattr(object_storage_importer, "_READERS", {"csv": "(SELECT 1 AS id)"})

    DataContract.import_from_source("adls", "abfss://container/orders/orders.csv")

    assert calls == ["setup_azure_connection"]
