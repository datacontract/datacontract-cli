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
