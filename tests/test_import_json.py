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
            "--format",
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
    actual = DataContract().import_from_source("json", json_file).to_yaml()
    actual_dict = yaml.safe_load(actual)

    # normalize paths in both dictionaries to use forward slashes and remove any ./tests/ prefix
    if "servers" in expected_dict and "production" in expected_dict["servers"]:
        if "path" in expected_dict["servers"]["production"]:
            expected_dict["servers"]["production"]["path"] = (
                expected_dict["servers"]["production"]["path"].replace("\\", "/").replace("./tests/", "")
            )

    if "models" in expected_dict and "product_simple" in expected_dict["models"]:
        if "description" in expected_dict["models"]["product_simple"]:
            expected_dict["models"]["product_simple"]["description"] = (
                expected_dict["models"]["product_simple"]["description"].replace("\\", "/").replace("./tests/", "")
            )

    if "servers" in actual_dict and "production" in actual_dict["servers"]:
        if "path" in actual_dict["servers"]["production"]:
            actual_dict["servers"]["production"]["path"] = (
                actual_dict["servers"]["production"]["path"].replace("\\", "/").replace("./tests/", "")
            )

    if "models" in actual_dict and "product_simple" in actual_dict["models"]:
        if "description" in actual_dict["models"]["product_simple"]:
            actual_dict["models"]["product_simple"]["description"] = (
                actual_dict["models"]["product_simple"]["description"].replace("\\", "/").replace("./tests/", "")
            )

    # compare the normalized dictionaries
    assert actual_dict == expected_dict

    # making sure the data contract is correct
    data_contract = DataContract(data_contract_str=actual)
    assert data_contract.lint(enabled_linters="none").has_passed()


def test_json_complex():
    # Get the expected and actual dictionaries
    expected_data_contract_file = "fixtures/import/json/product_detail.datacontract.yaml"
    with open(expected_data_contract_file, encoding="utf-8") as file:
        expected_json = file.read()
    expected_dict = yaml.safe_load(expected_json)

    json_file = "fixtures/import/json/product_detail.json"
    actual = DataContract().import_from_source("json", json_file).to_yaml()
    actual_dict = yaml.safe_load(actual)

    # normalize paths in both dictionaries to use forward slashes and remove any ./tests/ prefix
    if "servers" in expected_dict and "production" in expected_dict["servers"]:
        if "path" in expected_dict["servers"]["production"]:
            expected_dict["servers"]["production"]["path"] = (
                expected_dict["servers"]["production"]["path"].replace("\\", "/").replace("./tests/", "")
            )

    if "models" in expected_dict and "product_detail" in expected_dict["models"]:
        if "description" in expected_dict["models"]["product_detail"]:
            expected_dict["models"]["product_detail"]["description"] = (
                expected_dict["models"]["product_detail"]["description"].replace("\\", "/").replace("./tests/", "")
            )

    if "servers" in actual_dict and "production" in actual_dict["servers"]:
        if "path" in actual_dict["servers"]["production"]:
            actual_dict["servers"]["production"]["path"] = (
                actual_dict["servers"]["production"]["path"].replace("\\", "/").replace("./tests/", "")
            )

    if "models" in actual_dict and "product_detail" in actual_dict["models"]:
        if "description" in actual_dict["models"]["product_detail"]:
            actual_dict["models"]["product_detail"]["description"] = (
                actual_dict["models"]["product_detail"]["description"].replace("\\", "/").replace("./tests/", "")
            )

    # compare the normalized dictionaries
    assert actual_dict == expected_dict

    # making sure the data contract is correct
    data_contract = DataContract(data_contract_str=actual)
    assert data_contract.lint(enabled_linters="none").has_passed()


def test_ndjson():
    # Get the expected and actual dictionaries
    expected_data_contract_file = "fixtures/import/json/inventory_ndjson.datacontract.yaml"
    with open(expected_data_contract_file, encoding="utf-8") as file:
        expected_json = file.read()
    expected_dict = yaml.safe_load(expected_json)

    json_file = "fixtures/import/json/inventory_ndjson.json"
    actual = DataContract().import_from_source("json", json_file).to_yaml()
    actual_dict = yaml.safe_load(actual)

    # normalize paths in both dictionaries to use forward slashes and remove any ./tests/ prefix
    if "servers" in expected_dict and "production" in expected_dict["servers"]:
        if "path" in expected_dict["servers"]["production"]:
            expected_dict["servers"]["production"]["path"] = (
                expected_dict["servers"]["production"]["path"].replace("\\", "/").replace("./tests/", "")
            )

    if "models" in expected_dict and "inventory_ndjson" in expected_dict["models"]:
        if "description" in expected_dict["models"]["inventory_ndjson"]:
            expected_dict["models"]["inventory_ndjson"]["description"] = (
                expected_dict["models"]["inventory_ndjson"]["description"].replace("\\", "/").replace("./tests/", "")
            )

    if "servers" in actual_dict and "production" in actual_dict["servers"]:
        if "path" in actual_dict["servers"]["production"]:
            actual_dict["servers"]["production"]["path"] = (
                actual_dict["servers"]["production"]["path"].replace("\\", "/").replace("./tests/", "")
            )

    if "models" in actual_dict and "inventory_ndjson" in actual_dict["models"]:
        if "description" in actual_dict["models"]["inventory_ndjson"]:
            actual_dict["models"]["inventory_ndjson"]["description"] = (
                actual_dict["models"]["inventory_ndjson"]["description"].replace("\\", "/").replace("./tests/", "")
            )
    # compare the normalized dictionaries
    assert actual_dict == expected_dict

    # making sure the data contract is correct
    data_contract = DataContract(data_contract_str=actual)
    assert data_contract.lint(enabled_linters="none").has_passed()
