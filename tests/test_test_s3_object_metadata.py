import boto3
import pytest
from moto import mock_aws

from datacontract.data_contract import DataContract

datacontract = "fixtures/s3-object-metadata/datacontract.yaml"
bucket = "my-bucket"


@pytest.fixture
def s3(monkeypatch):
    monkeypatch.setenv("DATACONTRACT_S3_ACCESS_KEY_ID", "test-access")
    monkeypatch.setenv("DATACONTRACT_S3_SECRET_ACCESS_KEY", "test-secret")
    monkeypatch.setenv("DATACONTRACT_S3_REGION", "us-east-1")
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket=bucket)
        yield client


def _put(s3, key, size=1024, content_type="image/png"):
    s3.put_object(Bucket=bucket, Key=key, Body=b"\0" * size, ContentType=content_type)


def _failed(run):
    return {c.type: c for c in run.checks if c.result != "passed"}


def test_conforming_objects_pass(s3):
    _put(s3, "exports/nightly/2026-11-09/a.png")
    _put(s3, "exports/nightly/2026-11-10/b.png")

    run = DataContract(data_contract_file=datacontract).test()

    assert run.result == "passed", [(c.name, c.reason) for c in run.checks if c.result != "passed"]
    assert {c.field for c in run.checks if c.field} == {"name", "contentType", "size", "lastModified"}
    assert any(c.type == "servicelevel_freshness" for c in run.checks)


def test_violating_objects_fail(s3):
    _put(s3, "exports/nightly/2026-11-09/a.png")
    _put(s3, "exports/nightly/2026-11-09/huge.png", size=5242881)
    _put(s3, "exports/nightly/2026-11-09/b.png", content_type="image/jpeg")
    _put(s3, "exports/nightly/readme.txt", content_type="text/plain")

    run = DataContract(data_contract_file=datacontract).test()

    assert run.result == "failed"
    failed = _failed(run)
    assert set(failed) == {"field_regex", "field_invalid_values", "field_maximum"}
    assert failed["field_regex"].reason.endswith("was 1, expected = 0")
    assert failed["field_invalid_values"].reason.endswith("was 2, expected = 0")
    assert failed["field_maximum"].reason.endswith("was 1, expected = 0")


def test_empty_location_fails_the_row_count(s3):
    _put(s3, "elsewhere/a.png")

    run = DataContract(data_contract_file=datacontract).test()

    assert set(_failed(run)) == {"row_count", "servicelevel_freshness"}


def test_glob_location_lists_only_matching_objects(s3):
    _put(s3, "exports/nightly/2026-11-09/a.png")
    _put(s3, "exports/nightly/2026-11-09/b.png")
    _put(s3, "exports/nightly/2026-11-09/notes.txt", content_type="text/plain")
    # a single * stays within one path segment
    _put(s3, "exports/nightly/2026-11-09/nested/c.png", content_type="text/plain")
    # folder placeholders are no files
    s3.put_object(Bucket=bucket, Key="exports/nightly/2026-11-09/")
    with open(datacontract) as f:
        contract = f.read().replace("s3://my-bucket/exports/nightly/", "s3://my-bucket/exports/nightly/*/*.png")

    run = DataContract(data_contract_str=contract).test()

    assert run.result == "passed", [(c.name, c.reason) for c in run.checks if c.result != "passed"]


user_metadata_contract = """
apiVersion: v3.1.0
kind: DataContract
id: user-metadata
name: User metadata
version: 1.0.0
status: active
servers:
  - server: production
    type: s3
    location: s3://my-bucket/exports/
    format: metadata
schema:
  - name: files
    properties:
      - name: metadata
        logicalType: object
        properties:
          - name: Owner
            logicalType: string
            required: true
            logicalTypeOptions:
              pattern: "^team-"
"""


def test_user_defined_metadata_is_checked_per_key(s3):
    s3.put_object(Bucket=bucket, Key="exports/a.png", Body=b"", Metadata={"owner": "team-a"})
    s3.put_object(Bucket=bucket, Key="exports/b.png", Body=b"", Metadata={"owner": "bob"})
    s3.put_object(Bucket=bucket, Key="exports/c.png", Body=b"")

    run = DataContract(data_contract_str=user_metadata_contract).test()

    failed = _failed(run)
    assert set(failed) == {"field_required", "field_regex"}
    assert failed["field_required"].reason.endswith("was 1, expected = 0")
    assert failed["field_regex"].reason.endswith("was 1, expected = 0")


def test_user_defined_metadata_without_keys_is_a_map(s3):
    s3.put_object(Bucket=bucket, Key="exports/a.png", Body=b"", Metadata={"owner": "team-a"})
    s3.put_object(Bucket=bucket, Key="exports/b.png", Body=b"")
    contract = user_metadata_contract[: user_metadata_contract.index("        properties:")] + (
        "        quality:\n"
        "          - type: sql\n"
        "            query: SELECT COUNT(*) FROM files WHERE metadata['owner'] = 'team-a'\n"
        "            mustBe: 1\n"
    )

    run = DataContract(data_contract_str=contract).test()

    assert run.result == "passed", [(c.name, c.reason) for c in run.checks if c.result != "passed"]


@pytest.fixture
def gcs_responses(s3):
    """Answer like Google Cloud Storage: no storage class in the listing, x-goog-* headers on HeadObject."""

    def drop_storage_class(parsed, **kwargs):
        for obj in parsed.get("Contents", []):
            obj.pop("StorageClass", None)

    def goog_headers(parsed, **kwargs):
        parsed["Metadata"] = {}
        parsed["ResponseMetadata"]["HTTPHeaders"] |= {"x-goog-meta-owner": "team-a", "x-goog-storage-class": "NEARLINE"}

    events = boto3.DEFAULT_SESSION.events
    events.register("after-call.s3.ListObjectsV2", drop_storage_class)
    events.register("after-call.s3.HeadObject", goog_headers)
    yield s3
    events.unregister("after-call.s3.ListObjectsV2", drop_storage_class)
    events.unregister("after-call.s3.HeadObject", goog_headers)


def test_google_cloud_storage_metadata_and_storage_class_are_read(gcs_responses):
    gcs_responses.put_object(Bucket=bucket, Key="exports/a.png", Body=b"")
    contract = user_metadata_contract.replace(
        "    properties:\n      - name: metadata",
        "    properties:\n"
        "      - name: storageClass\n"
        "        logicalType: string\n"
        "        required: true\n"
        "        quality:\n"
        "          - metric: invalidValues\n"
        "            arguments:\n"
        "              validValues: [NEARLINE]\n"
        "            mustBe: 0\n"
        "      - name: metadata",
    )

    run = DataContract(data_contract_str=contract).test()

    assert run.result == "passed", [(c.name, c.reason) for c in run.checks if c.result != "passed"]
