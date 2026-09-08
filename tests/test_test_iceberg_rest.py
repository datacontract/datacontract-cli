"""`type: iceberg` against a real REST catalog: tabulario/iceberg-rest with MinIO for the data files.

The REST server and MinIO share a Docker network (the server writes and reads
the data files through the ``minio`` alias); the test and the CLI reach both
through their mapped ports on the host.
"""

import time

import pyarrow
import pytest
import requests
from testcontainers.core.container import DockerContainer
from testcontainers.core.network import Network
from testcontainers.minio import MinioContainer

from datacontract.data_contract import DataContract
from datacontract.model.run import ResultEnum

pytestmark = pytest.mark.slow

ACCESS_KEY = "iceberg-access"
SECRET_KEY = "iceberg-secret"
REGION = "us-east-1"
BUCKET = "warehouse"

CONTRACT = """apiVersion: v3.2.0
kind: DataContract
id: orders-iceberg-rest
name: Orders
version: 1.0.0
status: active
servers:
  - server: production
    type: iceberg
    catalog: rest
    catalogUrl: __CATALOG_URL__
    namespace: sales
schema:
  - name: orders
    properties:
      - name: order_id
        logicalType: string
        required: true
        unique: true
      - name: order_total
        logicalType: integer
        logicalTypeOptions:
          minimum: 0
      - name: attributes
        logicalType: map
        map:
          key:
            logicalType: string
          value:
            logicalType: integer
    quality:
      - type: sql
        description: two orders
        query: SELECT count(*) FROM orders
        mustBe: 2
"""

ORDERS = pyarrow.table(
    {
        "order_id": pyarrow.array(["1", "2"]),
        "order_total": pyarrow.array([100, 200], type=pyarrow.int64()),
        "attributes": pyarrow.array([[("a", 1)], [("b", 2)]], type=pyarrow.map_(pyarrow.string(), pyarrow.int64())),
    }
)


def _wait_for_catalog(url: str, timeout: float = 60) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if requests.get(f"{url}/v1/config", timeout=2).status_code == 200:
                return
        except requests.RequestException:
            pass
        time.sleep(1)
    raise TimeoutError(f"Iceberg REST catalog at {url} did not come up")


@pytest.fixture(scope="module")
def rest_catalog():
    """(catalog_url, s3_endpoint) of a running iceberg-rest server backed by MinIO, with sales.orders in it."""
    with Network() as network:
        minio = (
            MinioContainer(image="quay.io/minio/minio", access_key=ACCESS_KEY, secret_key=SECRET_KEY)
            .with_network(network)
            .with_network_aliases("minio")
        )
        with minio:
            minio.get_client().make_bucket(BUCKET)
            s3_endpoint = f"http://{minio.get_container_host_ip()}:{minio.get_exposed_port(9000)}"
            rest = (
                DockerContainer("tabulario/iceberg-rest:1.6.0")
                .with_network(network)
                .with_exposed_ports(8181)
                .with_env("CATALOG_WAREHOUSE", f"s3://{BUCKET}/")
                .with_env("CATALOG_IO__IMPL", "org.apache.iceberg.aws.s3.S3FileIO")
                .with_env("CATALOG_S3_ENDPOINT", "http://minio:9000")
                .with_env("CATALOG_S3_PATH__STYLE__ACCESS", "true")
                .with_env("AWS_ACCESS_KEY_ID", ACCESS_KEY)
                .with_env("AWS_SECRET_ACCESS_KEY", SECRET_KEY)
                .with_env("AWS_REGION", REGION)
            )
            with rest:
                catalog_url = f"http://{rest.get_container_host_ip()}:{rest.get_exposed_port(8181)}"
                _wait_for_catalog(catalog_url)
                _create_orders_table(catalog_url, s3_endpoint)
                yield catalog_url, s3_endpoint


def _create_orders_table(catalog_url: str, s3_endpoint: str) -> None:
    from pyiceberg.catalog import load_catalog

    catalog = load_catalog(
        "rest",
        **{
            "type": "rest",
            "uri": catalog_url,
            "s3.endpoint": s3_endpoint,
            "s3.access-key-id": ACCESS_KEY,
            "s3.secret-access-key": SECRET_KEY,
            "s3.region": REGION,
        },
    )
    catalog.create_namespace("sales")
    catalog.create_table("sales.orders", schema=ORDERS.schema).append(ORDERS)


@pytest.fixture
def iceberg_env(rest_catalog, monkeypatch):
    catalog_url, s3_endpoint = rest_catalog
    for name in [
        "DATACONTRACT_ICEBERG_CATALOG_URL",
        "DATACONTRACT_ICEBERG_CATALOG",
        "DATACONTRACT_ICEBERG_NAMESPACE",
        "DATACONTRACT_ICEBERG_WAREHOUSE",
        "DATACONTRACT_ICEBERG_CATALOG_TYPE",
        "DATACONTRACT_ICEBERG_TOKEN",
        "DATACONTRACT_ICEBERG_CREDENTIAL",
        "DATACONTRACT_S3_SESSION_TOKEN",
    ]:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("DATACONTRACT_S3_ACCESS_KEY_ID", ACCESS_KEY)
    monkeypatch.setenv("DATACONTRACT_S3_SECRET_ACCESS_KEY", SECRET_KEY)
    monkeypatch.setenv("DATACONTRACT_S3_REGION", REGION)
    monkeypatch.setenv("DATACONTRACT_ICEBERG_S3_ENDPOINT", s3_endpoint)
    return catalog_url


def test_test_against_a_rest_catalog(iceberg_env):
    run = DataContract(data_contract_str=CONTRACT.replace("__CATALOG_URL__", iceberg_env)).test()

    print(run.pretty())
    assert run.result == ResultEnum.passed, [c.reason for c in run.checks if c.reason]
    assert any(c.type == "field_nested_type" and c.result == ResultEnum.passed for c in run.checks)


def test_test_catches_a_violation_in_the_rest_catalog(iceberg_env):
    contract = CONTRACT.replace("__CATALOG_URL__", iceberg_env).replace("        mustBe: 2\n", "        mustBe: 3\n")

    run = DataContract(data_contract_str=contract).test()

    assert run.result == ResultEnum.failed
    failed = [c for c in run.checks if c.result == ResultEnum.failed]
    assert [c.name for c in failed] == ["two orders"]


def test_import_from_the_rest_catalog(iceberg_env):
    result = DataContract.import_from_source(
        "iceberg",
        iceberg_catalog_url=iceberg_env,
        iceberg_catalog="rest",
        iceberg_namespace="sales",
        iceberg_table="orders",
    )

    properties = {p.name: p for p in result.schema_[0].properties}
    assert properties["order_total"].logicalType == "integer"
    assert properties["attributes"].logicalType == "map"
    assert properties["attributes"].map.value.logicalType == "integer"
    assert result.servers[0].catalogUrl == iceberg_env
    assert result.servers[0].namespace == "sales"
