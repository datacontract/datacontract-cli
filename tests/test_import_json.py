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
            "fixtures/import/product_detail.json",
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
            "fixtures/import/product_detail.json",
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
    result = DataContract().import_from_source("json", "fixtures/import/product_detail.json")
    
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
    result = DataContract().import_from_source("json", "fixtures/import/product_simple.json")
    
    # verify the data contract was created successfully
    assert result is not None
    
    yaml_output = result.to_yaml()
    data = yaml.safe_load(yaml_output)
    assert "models" in data
    assert "product_simple" in data["models"]
    
    data_contract = DataContract(data_contract_str=yaml_output)
    assert data_contract.lint(enabled_linters="none").has_passed()