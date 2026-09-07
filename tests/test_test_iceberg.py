"""`type: iceberg` (ODCS v3.2.0): test and import through a REST catalog, with the catalog faked."""

from types import SimpleNamespace
from unittest.mock import patch

import pyarrow
import pytest
from open_data_contract_standard.model import Server
from pyiceberg.exceptions import NoSuchTableError
from pyiceberg.schema import Schema
from pyiceberg.types import IntegerType, MapType, NestedField, StringType

from datacontract.data_contract import DataContract
from datacontract.engines.ibis.connections.iceberg import catalog_properties, load_iceberg_catalog, table_identifier
from datacontract.model.exceptions import DataContractException
from datacontract.model.run import ResultEnum

CONTRACT = """apiVersion: v3.2.0
kind: DataContract
id: orders-iceberg
name: Orders
version: 1.0.0
status: active
servers:
  - server: production
    type: iceberg
    catalog: main
    catalogUrl: https://polaris.example.com/api/catalog
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

ORDERS_SCHEMA = Schema(
    NestedField(1, "order_id", StringType(), required=True),
    NestedField(2, "order_total", IntegerType(), required=False),
    NestedField(3, "attributes", MapType(4, StringType(), 5, IntegerType(), value_required=False), required=False),
    identifier_field_ids=[1],
)


class FakeCatalog:
    def __init__(self, tables: dict[str, pyarrow.Table]):
        self.tables = tables
        self.loaded: list[str] = []

    def load_table(self, identifier):
        self.loaded.append(identifier)
        if identifier not in self.tables:
            raise NoSuchTableError(identifier)
        arrow = self.tables[identifier]
        return SimpleNamespace(scan=lambda: SimpleNamespace(to_arrow=lambda: arrow), schema=lambda: ORDERS_SCHEMA)


@pytest.fixture
def catalog(monkeypatch):
    for name in [
        "DATACONTRACT_ICEBERG_CATALOG_URL",
        "DATACONTRACT_ICEBERG_CATALOG",
        "DATACONTRACT_ICEBERG_NAMESPACE",
        "DATACONTRACT_ICEBERG_WAREHOUSE",
        "DATACONTRACT_ICEBERG_TOKEN",
        "DATACONTRACT_ICEBERG_CREDENTIAL",
    ]:
        monkeypatch.delenv(name, raising=False)
    fake = FakeCatalog({"sales.orders": ORDERS})
    with patch("pyiceberg.catalog.load_catalog", return_value=fake) as load_catalog:
        fake.load_catalog = load_catalog
        yield fake


def test_test_reads_the_tables_from_the_catalog(catalog):
    run = DataContract(data_contract_str=CONTRACT).test()

    print(run.pretty())
    assert run.result == ResultEnum.passed
    assert catalog.loaded == ["sales.orders"]
    name, properties = catalog.load_catalog.call_args.args[0], catalog.load_catalog.call_args.kwargs
    assert name == "main"
    assert properties == {"type": "rest", "uri": "https://polaris.example.com/api/catalog"}
    assert any(c.type == "field_nested_type" and c.result == ResultEnum.passed for c in run.checks)


def test_a_missing_table_fails_with_the_identifier(catalog):
    contract = CONTRACT.replace("    namespace: sales\n", "    namespace: finance\n")

    run = DataContract(data_contract_str=contract).test()

    assert run.result == ResultEnum.failed
    reason = next(c.reason for c in run.checks if c.result == ResultEnum.failed)
    assert "finance.orders" in reason and "not found" in reason


@pytest.mark.parametrize("physical_name", ["orders", "sales.orders"])
def test_checks_use_the_logical_table_alias(catalog, physical_name):
    contract = CONTRACT.replace("  - name: orders\n", f"  - name: purchases\n    physicalName: {physical_name}\n")
    contract = contract.replace("FROM orders", "FROM purchases")

    run = DataContract(data_contract_str=contract).test()

    assert run.result == ResultEnum.passed, [c.reason for c in run.checks if c.reason]
    assert catalog.loaded == ["sales.orders"]


def test_configuration_overrides_and_credentials(catalog, monkeypatch):
    monkeypatch.setenv("DATACONTRACT_ICEBERG_CATALOG_URL", "https://nessie.example.com/iceberg")
    monkeypatch.setenv("DATACONTRACT_ICEBERG_WAREHOUSE", "s3://warehouse")
    monkeypatch.setenv("DATACONTRACT_ICEBERG_CREDENTIAL", "id:secret")
    monkeypatch.setenv("DATACONTRACT_S3_ACCESS_KEY_ID", "AKIA")
    monkeypatch.setenv("DATACONTRACT_S3_SECRET_ACCESS_KEY", "s3cr3t")
    monkeypatch.setenv("DATACONTRACT_S3_REGION", "eu-central-1")

    server = Server(server="production", type="iceberg", catalogUrl="https://polaris.example.com/api/catalog")

    assert catalog_properties(server) == {
        "type": "rest",
        "uri": "https://nessie.example.com/iceberg",
        "warehouse": "s3://warehouse",
        "credential": "id:secret",
        "s3.access-key-id": "AKIA",
        "s3.secret-access-key": "s3cr3t",
        "s3.region": "eu-central-1",
        "client.access-key-id": "AKIA",
        "client.secret-access-key": "s3cr3t",
        "client.region": "eu-central-1",
    }


def test_a_missing_catalog_url_is_an_error():
    with pytest.raises(DataContractException, match="catalogUrl"):
        catalog_properties(Server(server="production", type="iceberg"))


def test_table_identifier_uses_the_namespace_unless_the_name_carries_one():
    server = Server(server="production", type="iceberg", namespace="sales")
    assert table_identifier(server, "orders") == "sales.orders"
    assert table_identifier(server, "finance.invoices") == "finance.invoices"
    assert table_identifier(Server(server="production", type="iceberg"), "orders") == "orders"


def test_import_from_the_catalog_writes_schema_and_server(catalog):
    result = DataContract.import_from_source(
        "iceberg",
        iceberg_catalog_url="https://polaris.example.com/api/catalog",
        iceberg_catalog="main",
        iceberg_namespace="sales",
        iceberg_table="orders",
    )

    assert catalog.loaded == ["sales.orders"]
    schema = result.schema_[0]
    assert schema.name == "orders"
    assert [p.name for p in schema.properties] == ["order_id", "order_total", "attributes"]
    assert schema.properties[0].primaryKey is True
    assert schema.properties[2].logicalType == "map"
    assert schema.properties[2].map.value.logicalType == "integer"
    server = result.servers[0]
    assert server.type == "iceberg"
    assert server.catalog == "main"
    assert server.catalogUrl == "https://polaris.example.com/api/catalog"
    assert server.namespace == "sales"


def test_import_from_a_schema_file_still_works():
    result = DataContract.import_from_source("iceberg", "fixtures/iceberg/simple_schema.json", iceberg_table="orders")

    assert result.schema_[0].name == "orders"
    assert not result.servers


def test_import_qualified_table_can_be_tested_without_a_namespace_argument(catalog):
    result = DataContract.import_from_source(
        "iceberg", iceberg_catalog_url="https://polaris.example.com/api/catalog", iceberg_table="sales.orders"
    )

    assert result.schema_[0].name == "orders"
    run = DataContract(data_contract_str=result.to_yaml()).test()

    assert run.result == ResultEnum.passed, [c.reason for c in run.checks if c.reason]
    assert catalog.loaded == ["sales.orders", "sales.orders"]


# --- a real catalog: pyiceberg's SQL catalog with an Iceberg table written to a temp directory ------


@pytest.fixture
def sql_catalog(tmp_path, monkeypatch):
    pytest.importorskip("sqlalchemy")
    from pyiceberg.catalog import load_catalog

    uri = f"sqlite:///{tmp_path}/catalog.db"
    warehouse = f"file://{tmp_path}/warehouse"
    catalog = load_catalog("test", type="sql", uri=uri, warehouse=warehouse)
    catalog.create_namespace("sales")
    catalog.create_table("sales.orders", schema=ORDERS.schema).append(ORDERS)
    monkeypatch.setenv("DATACONTRACT_ICEBERG_CATALOG_TYPE", "sql")
    for name in ["DATACONTRACT_ICEBERG_TOKEN", "DATACONTRACT_ICEBERG_CREDENTIAL"]:
        monkeypatch.delenv(name, raising=False)
    return uri, warehouse


def test_test_against_a_real_iceberg_table(sql_catalog):
    uri, warehouse = sql_catalog
    contract = CONTRACT.replace(
        "    catalogUrl: https://polaris.example.com/api/catalog\n",
        f"    catalogUrl: {uri}\n    warehouse: {warehouse}\n",
    ).replace("    catalog: main\n", "    catalog: test\n")

    run = DataContract(data_contract_str=contract).test()

    print(run.pretty())
    assert run.result == ResultEnum.passed, [c.reason for c in run.checks if c.reason]


def test_import_from_a_real_iceberg_table(sql_catalog):
    uri, warehouse = sql_catalog

    result = DataContract.import_from_source(
        "iceberg", iceberg_catalog_url=uri, iceberg_catalog="test", iceberg_namespace="sales", iceberg_table="orders"
    )

    properties = {p.name: p for p in result.schema_[0].properties}
    assert properties["order_total"].logicalType == "integer"
    assert properties["attributes"].logicalType == "map"
    assert properties["attributes"].map.key.logicalType == "string"
    assert result.servers[0].catalogUrl == uri


# --- AWS-hosted catalogs: S3 Tables and Glue sign with SigV4 ------------------------------------


def test_s3_tables_endpoint_is_signed_with_sigv4(monkeypatch):
    for name in [
        "DATACONTRACT_ICEBERG_SIGNING_NAME",
        "DATACONTRACT_ICEBERG_PROPERTIES",
        "DATACONTRACT_S3_SESSION_TOKEN",
    ]:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("DATACONTRACT_S3_ACCESS_KEY_ID", "AKIA")
    monkeypatch.setenv("DATACONTRACT_S3_SECRET_ACCESS_KEY", "s3cr3t")
    monkeypatch.delenv("DATACONTRACT_S3_REGION", raising=False)
    server = Server(
        server="production",
        type="iceberg",
        catalogUrl="https://s3tables.eu-central-1.amazonaws.com/iceberg",
        warehouse="arn:aws:s3tables:eu-central-1:123456789012:bucket/my-bucket",
    )

    properties = catalog_properties(server)

    assert properties["rest.sigv4-enabled"] == "true"
    assert properties["rest.signing-name"] == "s3tables"
    assert properties["rest.signing-region"] == "eu-central-1"
    assert properties["warehouse"] == "arn:aws:s3tables:eu-central-1:123456789012:bucket/my-bucket"
    # the AWS keys serve both the signing (client.*) and the data files (s3.*)
    assert properties["client.access-key-id"] == "AKIA" and properties["s3.access-key-id"] == "AKIA"
    assert "token" not in properties and "credential" not in properties


def test_sso_credentials_reach_the_data_file_client(monkeypatch):
    for name in ["ACCESS_KEY_ID", "SECRET_ACCESS_KEY", "SESSION_TOKEN", "REGION"]:
        monkeypatch.delenv(f"DATACONTRACT_S3_{name}", raising=False)
    server = Server(server="p", type="iceberg", catalogUrl="https://s3tables.eu-central-1.amazonaws.com/iceberg")
    credentials = SimpleNamespace(access_key="sso-key", secret_key="sso-secret", token="sso-token")
    with patch("boto3.Session") as session, patch("pyiceberg.catalog.load_catalog") as load:
        session.return_value.get_credentials.return_value.get_frozen_credentials.return_value = credentials
        load_iceberg_catalog(server)

    properties = load.call_args.kwargs
    assert properties["s3.access-key-id"] == "sso-key"
    assert properties["s3.secret-access-key"] == "sso-secret"
    assert properties["s3.session-token"] == "sso-token"
    assert properties["s3.region"] == "eu-central-1"
    # The REST client retains its refreshable credential chain.
    assert "client.access-key-id" not in properties


def test_explicit_aws_credentials_do_not_resolve_the_default_chain(monkeypatch):
    monkeypatch.setenv("DATACONTRACT_S3_ACCESS_KEY_ID", "explicit-key")
    monkeypatch.setenv("DATACONTRACT_S3_SECRET_ACCESS_KEY", "explicit-secret")
    monkeypatch.setenv("DATACONTRACT_S3_SESSION_TOKEN", "explicit-token")
    server = Server(server="p", type="iceberg", catalogUrl="https://s3tables.eu-central-1.amazonaws.com/iceberg")
    with patch("boto3.Session") as session, patch("pyiceberg.catalog.load_catalog") as load:
        load_iceberg_catalog(server)

    session.assert_not_called()
    assert load.call_args.kwargs["s3.access-key-id"] == "explicit-key"
    assert load.call_args.kwargs["s3.session-token"] == "explicit-token"


def test_glue_endpoint_and_an_explicit_signing_name(monkeypatch):
    monkeypatch.delenv("DATACONTRACT_ICEBERG_SIGNING_NAME", raising=False)
    glue = Server(server="p", type="iceberg", catalogUrl="https://glue.us-east-1.amazonaws.com/iceberg")
    assert catalog_properties(glue)["rest.signing-name"] == "glue"

    monkeypatch.setenv("DATACONTRACT_ICEBERG_SIGNING_NAME", "s3tables")
    monkeypatch.setenv("DATACONTRACT_S3_REGION", "eu-west-1")
    proxied = Server(server="p", type="iceberg", catalogUrl="https://iceberg.internal.example.com")
    properties = catalog_properties(proxied)
    assert properties["rest.signing-name"] == "s3tables" and properties["rest.signing-region"] == "eu-west-1"

    monkeypatch.delenv("DATACONTRACT_ICEBERG_SIGNING_NAME", raising=False)
    polaris = Server(server="p", type="iceberg", catalogUrl="https://polaris.example.com/api/catalog")
    assert "rest.sigv4-enabled" not in catalog_properties(polaris)


def test_extra_catalog_properties_pass_through(monkeypatch):
    server = Server(server="p", type="iceberg", catalogUrl="https://polaris.example.com/api/catalog")

    monkeypatch.setenv("DATACONTRACT_ICEBERG_PROPERTIES", '{"scope": "PRINCIPAL_ROLE:ALL", "header.X-Custom": "1"}')
    assert catalog_properties(server)["scope"] == "PRINCIPAL_ROLE:ALL"

    monkeypatch.setenv("DATACONTRACT_ICEBERG_PROPERTIES", "scope=PRINCIPAL_ROLE:ALL, rest.signing-region=eu-west-1")
    assert catalog_properties(server)["rest.signing-region"] == "eu-west-1"

    monkeypatch.setenv("DATACONTRACT_ICEBERG_PROPERTIES", "{not json")
    with pytest.raises(DataContractException, match="not valid JSON"):
        catalog_properties(server)
