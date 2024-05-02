import boto3
from typer.testing import CliRunner
import logging
import yaml
from moto import mock_aws
import pytest

from datacontract.cli import app
from datacontract.data_contract import DataContract

logging.basicConfig(level=logging.INFO, force=True)

db_name = "test_database"
table_name = "test_table"


@pytest.fixture(scope="function")
def aws_credentials(monkeypatch):
    """Mocked AWS Credentials for moto."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")


@pytest.fixture(scope="function")
def setup_mock_glue(aws_credentials):
    with mock_aws():
        client = boto3.client("glue")

        client.create_database(
            DatabaseInput={
                "Name": db_name,
                "LocationUri": "s3://test_bucket/testdb",
            },
        )

        client.create_table(
            DatabaseName=db_name,
            TableInput={
                "Name": table_name,
                "StorageDescriptor": {
                    "Columns": [
                        {
                            "Name": "field_one",
                            "Type": "string",
                        },
                        {
                            "Name": "field_two",
                            "Type": "integer",
                        },
                        {
                            "Name": "field_three",
                            "Type": "timestamp",
                        },
                    ]
                },
                "PartitionKeys": [
                    {
                        "Name": "part_one",
                        "Type": "string",
                    },
                ],
            },
        )
        # everything after the yield will run after the fixture is used
        yield client


@mock_aws
def test_cli(setup_mock_glue):
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "import",
            "--format",
            "glue",
            "--source",
            "test_database",
        ],
    )
    assert result.exit_code == 0


@mock_aws
def test_import_glue_schema(setup_mock_glue):
    result = DataContract().import_from_source("glue", "test_database")

    with open("fixtures/glue/datacontract.yaml") as file:
        expected = file.read()

    print("Result", result.to_yaml())
    assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected)
    # Disable linters so we don't get "missing description" warnings
    assert DataContract(data_contract_str=expected).lint(enabled_linters=set()).has_passed()
