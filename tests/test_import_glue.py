import boto3
import pytest
import yaml
from moto import mock_aws
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract

# logging.basicConfig(level=logging.INFO, force=True)

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
                            "Comment": "Comment 1",
                        },
                        {
                            "Name": "field_two",
                            "Type": "int",
                        },
                        {
                            "Name": "field_three",
                            "Type": "timestamp",
                        },
                        {"Name": "field_four", "Type": "decimal(6,2)"},
                        {
                            "Name": "field_five",
                            "Type": "struct<sub_field_one:string, sub_field_two: boolean>",
                        },
                        {"Name": "field_six", "Type": "array<string>"},
                        {
                            "Name": "field_seven",
                            "Type": "array<struct<sub_field_three:string, sub_field_four:int>>",
                        },
                        {
                            "Name": "field_eight",
                            "Type": "map<string,int>",
                        },
                        {
                            "Name": "field_nine",
                            "Type": "decimal",
                        },
                        {
                            "Name": "field_ten",
                            "Type": "bigint",
                        },
                        {
                            "Name": "field_eleven",
                            "Type": "float",
                        },
                        {
                            "Name": "field_twelve",
                            "Type": "double",
                        },
                        {
                            "Name": "field_thirteen",
                            "Type": "timestamp",
                        },
                        {
                            "Name": "field_fourteen",
                            "Type": "date",
                        },
                        {
                            "Name": "field_fifteen",
                            "Type": "varchar",
                        },
                        {
                            "Name": "field_sixteen",
                            "Type": "varchar(255)",
                        },
                    ]
                },
                "PartitionKeys": [
                    {
                        "Name": "part_one",
                        "Type": "string",
                        "Comment": "Comment 2",
                    },
                    {
                        "Name": "part_two",
                        "Type": "date",
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
def test_cli_with_table_filters(setup_mock_glue):
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "import",
            "--format",
            "glue",
            "--source",
            "test_database",
            "--glue-table",
            "table_1",
            "--glue-table",
            "table_2",
        ],
    )
    assert result.exit_code == 0


@mock_aws
def test_import_glue_schema_without_glue_table_filter(setup_mock_glue):
    result = DataContract().import_from_source("glue", "test_database")

    with open("fixtures/glue/datacontract.yaml") as file:
        expected = file.read()

    print("Result", result.to_yaml())
    assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected)
    # Disable linters so we don't get "missing description" warnings
    assert DataContract(data_contract_str=expected).lint(enabled_linters=set()).has_passed()


@mock_aws
def test_import_glue_schema_with_glue_table_filter(setup_mock_glue):
    result = DataContract().import_from_source(format="glue", source="test_database", glue_table=[table_name])

    with open("fixtures/glue/datacontract.yaml") as file:
        expected = file.read()

    print("Result", result.to_yaml())
    assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected)
    # Disable linters so we don't get "missing description" warnings
    assert DataContract(data_contract_str=expected).lint(enabled_linters=set()).has_passed()


@mock_aws
def test_import_glue_schema_with_non_existent_glue_table_filter(setup_mock_glue):
    result = DataContract().import_from_source(format="glue", source="test_database", glue_table=["table_1"])

    # we specify a table that the Mock doesn't have and thus expect an empty result
    with open("fixtures/glue/datacontract-empty-model.yaml") as file:
        expected = file.read()

    print("Result", result.to_yaml())
    assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected)
    # Disable linters so we don't get "missing description" warnings
    assert DataContract(data_contract_str=expected).lint(enabled_linters=set()).has_passed()
