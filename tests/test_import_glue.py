import boto3
from typer.testing import CliRunner
import logging
import yaml
from moto import mock_aws
import os

from datacontract.cli import app
from datacontract.data_contract import DataContract

logging.basicConfig(level=logging.INFO, force=True)


def setup_mock_glue(db_name="test_database", table_name="test_table"):
    """Mocked AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"

    client = boto3.client("glue")

    client.create_database(
        DatabaseInput={
            "Name": db_name,
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


def test_cli():
    mock = mock_aws()
    mock.start()
    setup_mock_glue()

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
    mock.stop()


def test_import_glue_schema():
    mock = mock_aws()
    mock.start()
    setup_mock_glue()

    result = DataContract().import_from_source("glue", "test_database")

    with open("fixtures/glue/datacontract.yaml") as file:
        expected = file.read()

    print("Result", result.to_yaml())
    assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected)
    # Disable linters so we don't get "missing description" warnings
    assert DataContract(data_contract_str=expected).lint(enabled_linters=set()).has_passed()
    mock.stop()
