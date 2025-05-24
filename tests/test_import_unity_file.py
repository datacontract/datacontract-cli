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
    result = DataContract().import_from_source("unity", "fixtures/databricks-unity/import/unity_table_schema.json")

    with open("fixtures/databricks-unity/import/datacontract.yaml") as file:
        expected = file.read()

    print("Result:\n", result.to_yaml())
    assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected)
    assert DataContract(data_contract_str=expected).lint(enabled_linters="none").has_passed()


def test_cli_complex_types():
    print("running test_cli_complex_types")
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "import",
            "--format",
            "unity",
            "--source",
            "fixtures/databricks-unity/import/unity_table_schema_complex_types.json",
        ],
    )
    assert result.exit_code == 0


def test_import_unity_complex_types():
    print("running test_import_unity_complex_types")
    result = DataContract().import_from_source(
        "unity", "fixtures/databricks-unity/import/unity_table_schema_complex_types.json"
    )

    with open("fixtures/databricks-unity/import/datacontract_complex_types.yaml") as file:
        expected = file.read()

    print("Result:\n", result.to_yaml())
    assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected)
    assert DataContract(data_contract_str=expected).lint(enabled_linters="none").has_passed()


def test_import_unity_with_owner_and_id():
    print("running test_import_unity_with_owner_and_id")
    result = DataContract().import_from_source(
        "unity", "fixtures/databricks-unity/import/unity_table_schema.json", owner="sales-team", id="orders-v1"
    )

    # Verify owner and id are set correctly
    assert result.id == "orders-v1"
    assert result.info.owner == "sales-team"

    # Verify the rest of the contract is imported correctly
    with open("fixtures/databricks-unity/import/datacontract.yaml") as file:
        expected = file.read()
        expected_dict = yaml.safe_load(expected)
        result_dict = yaml.safe_load(result.to_yaml())

        # Remove owner and id from comparison since we set them differently
        expected_dict.pop("id", None)
        expected_dict["info"].pop("owner", None)
        result_dict.pop("id", None)
        result_dict["info"].pop("owner", None)

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
    assert output_dict["info"]["owner"] == "sales-team"
