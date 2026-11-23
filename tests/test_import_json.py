import pytest
import yaml
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract


def test_cli():
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "import",
            "json",
            "--source",
            "fixtures/import/json/product_detail.json",
        ],
    )
    assert result.exit_code == 0


def test_json_simple():
    # Get the expected and actual dictionaries
    expected_data_contract_file = "fixtures/import/json/product_simple.datacontract.yaml"
    with open(expected_data_contract_file, encoding="utf-8") as file:
        expected_json = file.read()
    expected_dict = yaml.safe_load(expected_json)

    json_file = "fixtures/import/json/product_simple.json"
    actual = DataContract.import_from_source("json", json_file).to_yaml()
    actual_dict = yaml.safe_load(actual)

    # compare the normalized dictionaries
    assert actual_dict == expected_dict


def test_json_complex():
    # Get the expected and actual dictionaries
    expected_data_contract_file = "fixtures/import/json/product_detail.datacontract.yaml"
    with open(expected_data_contract_file, encoding="utf-8") as file:
        expected_json = file.read()
    expected_dict = yaml.safe_load(expected_json)

    json_file = "fixtures/import/json/product_detail.json"
    actual = DataContract.import_from_source("json", json_file).to_yaml()
    actual_dict = yaml.safe_load(actual)

    # compare the normalized dictionaries
    assert actual_dict == expected_dict


def test_ndjson():
    # Get the expected and actual dictionaries
    expected_data_contract_file = "fixtures/import/json/inventory_ndjson.datacontract.yaml"
    with open(expected_data_contract_file, encoding="utf-8") as file:
        expected_json = file.read()
    expected_dict = yaml.safe_load(expected_json)

    json_file = "fixtures/import/json/inventory_ndjson.json"
    actual = DataContract.import_from_source("json", json_file).to_yaml()
    actual_dict = yaml.safe_load(actual)

    # compare the normalized dictionaries
    assert actual_dict == expected_dict


def _has_examples(node) -> bool:
    if isinstance(node, dict):
        return "examples" in node or any(_has_examples(v) for v in node.values())
    return isinstance(node, list) and any(_has_examples(v) for v in node)


@pytest.mark.parametrize(
    "source", ["fixtures/import/json/product_detail.json", "fixtures/import/json/inventory_ndjson.json"]
)
def test_cli_examples_are_on_unless_no_examples(source):
    """Nested properties and NDJSON records leave out their examples too."""
    default = CliRunner().invoke(app, ["import", "json", "--source", source])
    result = CliRunner().invoke(app, ["import", "json", "--source", source, "--no-examples"])

    assert default.exit_code == 0 and result.exit_code == 0, result.output
    assert _has_examples(yaml.safe_load(default.stdout))
    assert not _has_examples(yaml.safe_load(result.stdout))
