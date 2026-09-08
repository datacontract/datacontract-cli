"""Opt-in AWS S3 Tables E2E tests (real CLI subprocesses, no catalog mocks).

Set AWS_PROFILE and DATACONTRACT_TEST_S3_TABLES_WAREHOUSE to a playground table
bucket ARN. The fixture creates a unique namespace and a three-row table, then
deletes only those resources. AWS request/storage charges apply.
"""

import json
import os
import subprocess
import sys
from datetime import date, datetime, time, timezone
from decimal import Decimal
from uuid import uuid4

import boto3
import pyarrow as pa
import pytest
import yaml
from open_data_contract_standard.model import Server

from datacontract.engines.ibis.connections.iceberg import load_iceberg_catalog

WAREHOUSE = os.getenv("DATACONTRACT_TEST_S3_TABLES_WAREHOUSE")
pytestmark = pytest.mark.skipif(not WAREHOUSE, reason="Set DATACONTRACT_TEST_S3_TABLES_WAREHOUSE to opt in to AWS")


@pytest.fixture(scope="module")
def s3_table():
    arn = WAREHOUSE.split(":", 5)
    assert arn[:3] == ["arn", "aws", "s3tables"] and arn[5].startswith("bucket/")
    assert boto3.client("sts").get_caller_identity()["Account"] == arn[4], "Use a bucket in the signed-in account"
    namespace = f"datacontract_e2e_{uuid4().hex[:12]}"
    endpoint = f"https://s3tables.{arn[3]}.amazonaws.com/iceberg"
    catalog = load_iceberg_catalog(Server(server="test", type="iceberg", catalogUrl=endpoint, warehouse=WAREHOUSE))
    schema = pa.schema(
        [
            pa.field("order_id", pa.string(), nullable=False),
            pa.field("quantity", pa.int64()),
            pa.field("total", pa.decimal128(12, 2)),
            pa.field("paid", pa.bool_()),
            pa.field("order_date", pa.date32()),
            pa.field("order_time", pa.time64("us")),
            pa.field("created_at", pa.timestamp("us")),
            pa.field("updated_at", pa.timestamp("us", tz="UTC")),
            pa.field("tags", pa.list_(pa.string())),
            pa.field("attributes", pa.map_(pa.string(), pa.int64())),
            pa.field("shipping", pa.struct([pa.field("city", pa.string()), pa.field("priority", pa.int32())])),
            pa.field("payload", pa.binary()),
            pa.field("fingerprint", pa.binary(4)),
        ]
    )
    rows = [
        dict(
            order_id=f"order-{i}",
            quantity=i,
            total=Decimal(f"{i * 10}.50"),
            paid=True,
            order_date=date(2026, 9, 5),
            order_time=time(12, i),
            created_at=datetime(2026, 9, 5, 12, i),
            updated_at=datetime(2026, 9, 5, 12, i, tzinfo=timezone.utc),
            tags=["synthetic", "test"],
            attributes=[("items", i)],
            shipping={"city": "Berlin", "priority": i},
            payload=b"test",
            fingerprint=b"1234",
        )
        for i in range(1, 4)
    ]
    catalog.create_namespace(namespace)
    created = False
    try:
        table = catalog.create_table(f"{namespace}.orders", schema=schema)
        created = True
        table.append(pa.Table.from_pylist(rows, schema=schema))
        assert catalog.load_table(f"{namespace}.orders").scan().to_arrow().num_rows == 3
        yield endpoint, namespace
    finally:
        # The direct REST endpoint requires purge=true; use the equivalent AWS
        # API so this also works with clients whose drop_table sends purge=false.
        client = boto3.client("s3tables", region_name=arn[3])
        if created:
            client.delete_table(tableBucketARN=WAREHOUSE, namespace=namespace, name="orders")
        client.delete_namespace(tableBucketARN=WAREHOUSE, namespace=namespace)


def cli(*args, expected_code=0):
    result = subprocess.run(
        [sys.executable, "-c", "from datacontract.cli import main; main()", *map(str, args)],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == expected_code, result.stdout + result.stderr
    return result.stdout


def import_contract(s3_table, tmp_path, qualified=False):
    endpoint, namespace = s3_table
    output = tmp_path / "orders.odcs.yaml"
    identifier = ["--table", f"{namespace}.orders"] if qualified else ["--namespace", namespace, "--table", "orders"]
    # Deliberately omit --catalog: the importer must supply a valid default.
    cli("import", "iceberg", "--catalog-url", endpoint, "--warehouse", WAREHOUSE, *identifier, "--output", output)
    return output, yaml.safe_load(output.read_text())


@pytest.mark.parametrize("qualified", [False, True])
def test_import_lint_and_test(s3_table, tmp_path, qualified):
    output, contract = import_contract(s3_table, tmp_path, qualified)
    props = {p["name"]: p for p in contract["schema"][0]["properties"]}
    assert props["order_time"]["logicalType"] == "time"
    assert props["created_at"]["logicalType"] == props["updated_at"]["logicalType"] == "timestamp"
    assert props["attributes"]["map"]["value"]["logicalType"] == "integer"
    assert props["shipping"]["logicalType"] == "object"
    assert "logicalType" not in props["payload"]
    assert "logicalType" not in props["fingerprint"]
    cli("lint", output)
    cli("test", output)


@pytest.mark.parametrize(
    "violation", [None, "row_count", "minimum", "type", "nested_type", "missing_column", "missing_table"]
)
def test_aliased_table_quality_and_failures(s3_table, tmp_path, violation):
    output, contract = import_contract(s3_table, tmp_path, qualified=True)
    schema = contract["schema"][0]
    schema["name"] = "purchases"
    props = {p["name"]: p for p in schema["properties"]}
    props["order_id"].update(required=True, unique=True)
    props["quantity"]["logicalTypeOptions"] = {"minimum": 1}
    schema["quality"] = [{"type": "sql", "query": "SELECT count(*) FROM purchases", "mustBe": 3}]
    if violation == "row_count":
        schema["quality"][0]["mustBe"] = 4
    elif violation == "minimum":
        props["quantity"]["logicalTypeOptions"]["minimum"] = 2
    elif violation == "type":
        props["quantity"]["logicalType"] = "string"
        props["quantity"].pop("logicalTypeOptions")
    elif violation == "nested_type":
        props["attributes"]["map"]["value"]["logicalType"] = "string"
    elif violation == "missing_column":
        schema["properties"].append({"name": "missing", "logicalType": "string"})
    elif violation == "missing_table":
        schema["physicalName"] = f"{s3_table[1]}.missing"
    output.write_text(yaml.safe_dump(contract, sort_keys=False))
    cli("lint", output)
    report = tmp_path / "result.json"
    cli("test", output, "--output", report, "--output-format", "json", expected_code=1 if violation else 0)
    checks = json.loads(report.read_text())["checks"]
    failed = [c for c in checks if c["result"] == "failed"]
    assert bool(failed) == bool(violation)
    expected_failure = {
        "row_count": "sql",
        "minimum": "minimum",
        "type": "type",
        "nested_type": "nested",
        "missing_column": "present",
        "missing_table": "missing_table",
    }
    if violation:
        assert any(
            expected_failure[violation] in c["type"] or expected_failure[violation] in c["name"] for c in failed
        ), failed
