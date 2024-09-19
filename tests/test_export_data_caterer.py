import os
import sys

import yaml
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.export.data_caterer_converter import to_data_caterer_generate_yaml
from datacontract.model.data_contract_specification import DataContractSpecification


def test_cli():
    runner = CliRunner()
    result = runner.invoke(app, ["export", "./fixtures/export/datacontract.yaml", "--format", "data-caterer"])
    assert result.exit_code == 0


def test_to_data_caterer():
    data_contract = DataContractSpecification.from_string(
        read_file("fixtures/data-caterer/export/datacontract_nested.yaml")
    )
    expected_data_caterer_model = _get_expected_data_caterer_yaml("s3://covid19-lake/enigma-jhu/json/*.json")

    data_caterer_yaml = to_data_caterer_generate_yaml(data_contract, None)
    result = yaml.safe_load(data_caterer_yaml)

    assert result == yaml.safe_load(expected_data_caterer_model)


def test_to_data_caterer_with_server():
    data_contract = DataContractSpecification.from_string(
        read_file("fixtures/data-caterer/export/datacontract_nested.yaml")
    )
    expected_data_caterer_model = _get_expected_data_caterer_yaml("s3://covid19-lake-prod/enigma-jhu/json/*.json")

    data_caterer_yaml = to_data_caterer_generate_yaml(data_contract, "s3-json-prod")
    result = yaml.safe_load(data_caterer_yaml)

    assert result == yaml.safe_load(expected_data_caterer_model)


def _get_expected_data_caterer_yaml(path: str):
    return f"""
name: Orders Unit Test
steps:
- name: orders
  type: json
  options:
    path: {path}
  schema:
  - name: order_id
    type: string
    generator:
      options:
        isUnique: true
        minLength: 8
        maxLength: 10
        regex: ^B[0-9]+$
  - name: order_total
    type: decimal
    generator:
      options:
        min: 0
        max: 1000000
  - name: order_status
    type: string
    generator:
      options:
        oneOf:
        - pending
        - shipped
        - delivered
  - name: address
    type: struct
    schema:
      fields:
      - name: street
        type: string
      - name: city
        type: string
"""


def read_file(file):
    if not os.path.exists(file):
        print(f"The file '{file}' does not exist.")
        sys.exit(1)
    with open(file, "r") as file:
        file_content = file.read()
    return file_content
