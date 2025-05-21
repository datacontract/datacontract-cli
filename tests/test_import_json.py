import os
from pathlib import Path

import yaml
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract


def test_cli_import_product_json():
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


def test_cli_import_product_json_with_output(tmp_path: Path):
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "import",
            "--format",
            "json",
            "--source",
            "fixtures/import/json/product_detail.json",
            "--output",
            tmp_path / "datacontract.yaml",
        ],
    )
    assert result.exit_code == 0
    assert os.path.exists(tmp_path / "datacontract.yaml")

    with open(tmp_path / "datacontract.yaml") as file:
        actual = file.read()

    # validate the content has expected structure
    data = yaml.safe_load(actual)
    assert "models" in data
    assert "product_detail" in data["models"]

    # validate key fields from the model
    model = data["models"]["product_detail"]
    assert model["type"] == "object"
    assert "fields" in model
    assert "identification" in model["fields"]
    assert "pharmaceuticalContent" in model["fields"]
    assert "ecommerceContent" in model["fields"]


def test_direct_api_import_product_json():
    result = DataContract().import_from_source("json", "fixtures/import/json/product_detail.json")

    # convert to YAML and validate structure
    yaml_output = result.to_yaml()
    data = yaml.safe_load(yaml_output)

    # check key components of the data contract
    assert "models" in data
    assert "product_detail" in data["models"]

    # verify the nested fields structure
    product_model = data["models"]["product_detail"]
    assert product_model["type"] == "object"
    assert "fields" in product_model

    # check identification field
    assert "identification" in product_model["fields"]
    identification = product_model["fields"]["identification"]
    assert identification["type"] == "object"
    assert "fields" in identification
    assert "gtin" in identification["fields"]

    # check pharmaceuticalContent field
    assert "pharmaceuticalContent" in product_model["fields"]
    pharma_content = product_model["fields"]["pharmaceuticalContent"]
    assert pharma_content["type"] == "array"
    assert "items" in pharma_content

    # validate that lint passes on the generated contract
    data_contract = DataContract(data_contract_str=yaml_output)

    assert data_contract.lint(enabled_linters="none").has_passed()


def test_simple_product_json_import():
    result = DataContract().import_from_source("json", "fixtures/import/json/product_simple.json")

    # verify the data contract was created successfully
    assert result is not None

    yaml_output = result.to_yaml()
    data = yaml.safe_load(yaml_output)
    assert "models" in data
    assert "product_simple" in data["models"]

    data_contract = DataContract(data_contract_str=yaml_output)
    assert data_contract.lint(enabled_linters="none").has_passed()


def test_json_expected():
    # Get the expected and actual dictionaries
    expected_data_contract_file = "fixtures/import/json/productsimple.datacontract.yaml"
    with open(expected_data_contract_file) as file:
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

def test_ndjson_import():
    result = DataContract().import_from_source("json", "fixtures/import/json/inventory_ndjson.json")

    # verify the data contract was created successfully
    assert result is not None

    yaml_output = result.to_yaml()
    data = yaml.safe_load(yaml_output)
    assert "models" in data
    data_contract = DataContract(data_contract_str=yaml_output)
    assert data_contract.lint(enabled_linters="none").has_passed()
    
def test_ndjson_expected():
    # Get the expected and actual dictionaries
    expected_data_contract_file = "fixtures/import/json/inventory_ndjson.datacontract.yaml"
    with open(expected_data_contract_file) as file:
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