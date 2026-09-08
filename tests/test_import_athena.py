"""Tests for the Athena importer, run against a moto-mocked Glue Data Catalog."""

import boto3
import pytest
import yaml
from moto import mock_aws
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract
from datacontract.engines.checks.physical_type_match import physical_type_matches
from datacontract.model.exceptions import DataContractException
from datacontract.model.run import ResultEnum

DATABASE = "my_database"
STAGING_DIR = "s3://my-bucket/athena-results/"


@pytest.fixture
def aws_credentials(monkeypatch):
    """Mocked AWS Credentials for moto."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "eu-central-1")


@pytest.fixture
def setup_mock_glue(aws_credentials):
    with mock_aws():
        client = boto3.client("glue")
        client.create_database(DatabaseInput={"Name": DATABASE, "LocationUri": "s3://my-bucket/warehouse"})
        client.create_table(
            DatabaseName=DATABASE,
            TableInput={
                "Name": "orders",
                "StorageDescriptor": {
                    "Columns": [
                        {"Name": "order_id", "Type": "string", "Comment": "The order id"},
                        {"Name": "order_total", "Type": "decimal(10,2)"},
                        {"Name": "line_count", "Type": "int"},
                        {"Name": "ordered_at", "Type": "timestamp"},
                        {"Name": "tags", "Type": "array<string>"},
                        {"Name": "payload", "Type": "binary"},
                    ]
                },
                "PartitionKeys": [{"Name": "order_date", "Type": "date"}],
            },
        )
        client.create_table(
            DatabaseName=DATABASE,
            TableInput={"Name": "customers", "StorageDescriptor": {"Columns": [{"Name": "id", "Type": "string"}]}},
        )
        yield client


def _import(**kwargs):
    kwargs.setdefault("schema", DATABASE)
    kwargs.setdefault("staging_dir", STAGING_DIR)
    return DataContract.import_from_source("athena", **kwargs)


@mock_aws
def test_import_athena(setup_mock_glue):
    result = _import(region="eu-central-1", athena_table=["orders"])

    expected = """
apiVersion: v3.2.0
kind: DataContract
id: my-data-contract
name: My Data Contract
version: 1.0.0
status: draft
servers:
  - server: athena
    type: athena
    catalog: awsdatacatalog
    schema: my_database
    regionName: eu-central-1
    stagingDir: s3://my-bucket/athena-results/
schema:
  - name: orders
    physicalName: orders
    logicalType: object
    physicalType: table
    properties:
      - name: order_id
        logicalType: string
        physicalType: varchar
        description: The order id
      - name: order_total
        logicalType: number
        physicalType: decimal
        customProperties:
          - property: precision
            value: 10
          - property: scale
            value: 2
      - name: line_count
        logicalType: integer
        physicalType: int
      - name: ordered_at
        logicalType: timestamp
        physicalType: timestamp
      - name: tags
        logicalType: array
        physicalType: array<string>
        items:
          name: items
          logicalType: string
          physicalType: varchar
      - name: payload
        logicalType: string
        physicalType: varbinary
      - name: order_date
        logicalType: date
        physicalType: date
        required: true
    """

    print("Result", result.to_yaml())
    assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected)


@mock_aws
def test_imported_physical_types_match_what_athena_reports(setup_mock_glue):
    """Glue stores the Hive spelling; the contract must carry what Athena reports back."""
    result = _import(athena_table=["orders"])
    properties = {prop.name: prop.physicalType for prop in result.schema_[0].properties}

    # what Athena's catalog returns for these columns
    reported = {
        "order_id": "varchar",
        "order_total": "decimal(10,2)",
        "line_count": "integer",
        "ordered_at": "timestamp(3)",
        "tags": "array(varchar)",
        "payload": "varbinary",
        "order_date": "date",
    }
    for name, actual in reported.items():
        matches, reason = physical_type_matches(properties[name], actual, "athena")
        assert matches is True, f"{name}: declared '{properties[name]}' vs Athena '{actual}' -> {reason}"


@mock_aws
def test_import_athena_produces_a_valid_contract(setup_mock_glue):
    result = _import()

    run = DataContract(data_contract_str=result.to_yaml()).lint()

    assert run.result == ResultEnum.passed


@mock_aws
def test_import_athena_imports_all_tables_by_default(setup_mock_glue):
    result = _import()

    assert [schema.name for schema in result.schema_] == ["customers", "orders"]


@mock_aws
def test_import_athena_defaults_the_catalog(setup_mock_glue):
    result = _import()

    assert result.servers[0].catalog == "awsdatacatalog"


@mock_aws
def test_import_athena_omits_an_unset_region(setup_mock_glue):
    result = _import()

    assert result.servers[0].regionName is None


@mock_aws
def test_import_athena_fails_on_an_unknown_table(setup_mock_glue):
    with pytest.raises(DataContractException) as exc_info:
        _import(athena_table=["does_not_exist"])

    assert "No tables found" in exc_info.value.reason


def test_import_athena_requires_a_schema():
    with pytest.raises(DataContractException) as exc_info:
        DataContract.import_from_source("athena", staging_dir=STAGING_DIR)

    assert "Athena database is required" in exc_info.value.reason


def test_import_athena_requires_a_staging_dir():
    with pytest.raises(DataContractException) as exc_info:
        DataContract.import_from_source("athena", schema=DATABASE)

    assert "staging directory is required" in exc_info.value.reason


@mock_aws
def test_cli(setup_mock_glue):
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["import", "athena", "--schema", DATABASE, "--staging-dir", STAGING_DIR],
    )

    assert result.exit_code == 0
    # `--schema` is the Athena database here, not the v0.12.0 `--json-schema`
    assert "--json-schema" not in result.output
    assert "schema: my_database" in result.output
