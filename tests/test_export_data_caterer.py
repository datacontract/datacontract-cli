import os
import sys

import yaml
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.export.data_caterer_converter import to_data_caterer_generate_yaml
from datacontract.model.data_contract_specification import DataContractSpecification, Server


def test_cli():
    runner = CliRunner()
    result = runner.invoke(app, ["export", "./fixtures/export/datacontract.yaml", "--format", "data-caterer"])
    assert result.exit_code == 0


def test_to_data_caterer():
    data_contract = DataContractSpecification.from_string(
        read_file("fixtures/data-caterer/export/datacontract_nested.yaml")
    )
    expected_data_caterer_model = """
name: Orders Unit Test
steps:
- name: orders
  type: csv
  options: {}
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

    data_caterer_yaml = to_data_caterer_generate_yaml(data_contract, Server())
    result = yaml.safe_load(data_caterer_yaml)

    assert result == yaml.safe_load(expected_data_caterer_model)


def read_file(file):
    if not os.path.exists(file):
        print(f"The file '{file}' does not exist.")
        sys.exit(1)
    with open(file, "r") as file:
        file_content = file.read()
    return file_content
