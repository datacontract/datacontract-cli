import yaml
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract

# logging.basicConfig(level=logging.DEBUG, force=True)


def test_cli():
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "import",
            "--format",
            "jsonschema",
            "--source",
            "fixtures/import/orders.json",
        ],
    )
    assert result.exit_code == 0


def test_import_json_schema_orders():
    result = DataContract().import_from_source("jsonschema", "fixtures/import/orders_union-types.json")

    with open("fixtures/import/orders_union-types_datacontract.yml") as file:
        expected = file.read()

    print("Result:\n", result.to_yaml())
    assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected)
    assert DataContract(data_contract_str=expected).lint(enabled_linters="none").has_passed()


def test_import_json_schema_football():
    result = DataContract().import_from_source("jsonschema", "fixtures/import/football.json")

    with open("fixtures/import/football-datacontract.yml") as file:
        expected = file.read()
        assert DataContract(data_contract_str=expected).lint(enabled_linters="none").has_passed()

    print("Result:\n", result.to_yaml())
    assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected)
