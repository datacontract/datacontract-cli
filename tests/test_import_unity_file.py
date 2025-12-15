import yaml
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract

# logging.basicConfig(level=logging.DEBUG, force=True)


def test_cli():
    print("running test_cli")
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "import",
            "--format",
            "unity",
            "--source",
            "fixtures/databricks-unity/import/unity_table_schema.json",
        ],
    )
    assert result.exit_code == 0


def test_import_unity():
    print("running test_import_unity")
    result = DataContract.import_from_source("unity", "fixtures/databricks-unity/import/unity_table_schema.json")

    with open("fixtures/databricks-unity/import/datacontract.yaml") as file:
        expected = file.read()

    result_yaml = result.to_yaml()
    print("Result:\n", result_yaml)
    assert yaml.safe_load(result_yaml) == yaml.safe_load(expected)
    assert DataContract(data_contract_str=expected).lint().has_passed()


def test_import_unity_with_owner_and_id():
    print("running test_import_unity_with_owner_and_id")
    result = DataContract.import_from_source(
        "unity", "fixtures/databricks-unity/import/unity_table_schema.json", owner="sales-team", id="orders-v1"
    )

    # Verify owner and id are set correctly
    assert result.id == "orders-v1"
    assert result.team.name == "sales-team"

    # Verify the rest of the contract is imported correctly
    with open("fixtures/databricks-unity/import/datacontract.yaml") as file:
        expected = file.read()
        expected_dict = yaml.safe_load(expected)
        result_dict = yaml.safe_load(result.to_yaml())

        # Remove team and id from comparison since we set them differently
        expected_dict.pop("id", None)
        expected_dict.pop("team", None)
        result_dict.pop("id", None)
        result_dict.pop("team", None)

        assert result_dict == expected_dict


def test_cli_with_owner_and_id():
    print("running test_cli_with_owner_and_id")
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "import",
            "--format",
            "unity",
            "--source",
            "fixtures/databricks-unity/import/unity_table_schema.json",
            "--owner",
            "sales-team",
            "--id",
            "orders-v1",
        ],
    )
    assert result.exit_code == 0

    # Parse the output YAML
    output_dict = yaml.safe_load(result.stdout)

    # Verify owner and id are set correctly
    assert output_dict["id"] == "orders-v1"
    assert output_dict["team"]["name"] == "sales-team"
