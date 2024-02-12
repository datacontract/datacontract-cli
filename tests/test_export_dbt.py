import json
import logging
import os
import sys
import yaml

from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.export.dbt_converter import to_dbt
from datacontract.model.data_contract_specification import \
    DataContractSpecification

logging.basicConfig(level=logging.DEBUG, force=True)


def test_cli():
    runner = CliRunner()
    result = runner.invoke(app, [
        "export",
        "./examples/local-json/datacontract.yaml",
        "--format", "dbt"
    ])
    assert result.exit_code == 0


def test_to_dbt():
    data_contract = DataContractSpecification.from_string(read_file("./examples/export/datacontract.yaml"))
    expected_dbt_model = """
version: 2
models:
  - name: orders    
    config:
      materialized: table
      contract:
        enforced: true
    columns:
      - name: order_id
        data_type: text
        constraints:
          - type: not_null
          - type: unique
      - name: order_total
        data_type: integer
        constraints:
          - type: not_null    
"""

    result = yaml.safe_load(to_dbt(data_contract))

    assert result == yaml.safe_load(expected_dbt_model)


def read_file(file):
    if not os.path.exists(file):
        print(f"The file '{file}' does not exist.")
        sys.exit(1)
    with open(file, 'r') as file:
        file_content = file.read()
    return file_content
