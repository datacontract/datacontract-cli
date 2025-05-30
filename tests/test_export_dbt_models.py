import os
import sys

import yaml
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.export.dbt_converter import to_dbt_models_yaml
from datacontract.model.data_contract_specification import DataContractSpecification

# logging.basicConfig(level=logging.DEBUG, force=True)


def test_cli():
    runner = CliRunner()
    result = runner.invoke(app, ["export", "./fixtures/export/datacontract.yaml", "--format", "dbt"])
    assert result.exit_code == 0


def test_to_dbt_models():
    data_contract = DataContractSpecification.from_file("fixtures/export/datacontract.yaml")
    expected_dbt_model = """
version: 2
models:
  - name: orders
    config:
      meta:
        owner: checkout
        data_contract: orders-unit-test
      materialized: table
      contract:
        enforced: true
    description: The orders model
    columns:
      - name: order_id
        data_type: VARCHAR
        constraints:
          - type: not_null
          - type: unique
        data_tests:
          - dbt_expectations.expect_column_value_lengths_to_be_between:
              min_value: 8
              max_value: 10
          - dbt_expectations.expect_column_values_to_match_regex:
              regex: ^B[0-9]+$
        meta:
          classification: sensitive
          pii: true
        tags:
          - order_id
      - name: order_total
        data_type: NUMBER
        constraints:
          - type: not_null
        description: The order_total field
        data_tests:
          - dbt_expectations.expect_column_values_to_be_between:
               min_value: 0
               max_value: 1000000
      - name: order_status
        data_type: TEXT
        constraints:
          - type: not_null
        data_tests:
          - accepted_values:
              values:
                - 'pending'
                - 'shipped'
                - 'delivered'
"""

    result = yaml.safe_load(to_dbt_models_yaml(data_contract))

    assert result == yaml.safe_load(expected_dbt_model)


def test_to_dbt_models_with_server():
    data_contract = DataContractSpecification.from_file("fixtures/export/datacontract.yaml")
    expected_dbt_model = """
version: 2
models:
  - name: orders
    config:
      meta:
        owner: checkout
        data_contract: orders-unit-test
      materialized: table
      contract:
        enforced: true
    description: The orders model
    columns:
      - name: order_id
        data_type: STRING
        constraints:
          - type: not_null
          - type: unique
        data_tests:
          - dbt_expectations.expect_column_value_lengths_to_be_between:
              min_value: 8
              max_value: 10
          - dbt_expectations.expect_column_values_to_match_regex:
              regex: ^B[0-9]+$
        meta:
          classification: sensitive
          pii: true
        tags:
          - order_id
      - name: order_total
        data_type: INT64
        constraints:
          - type: not_null
        description: The order_total field
        data_tests:
          - dbt_expectations.expect_column_values_to_be_between:
               min_value: 0
               max_value: 1000000
      - name: order_status
        data_type: STRING
        constraints:
          - type: not_null
        data_tests:
          - accepted_values:
              values:
                - 'pending'
                - 'shipped'
                - 'delivered'
"""

    result = yaml.safe_load(to_dbt_models_yaml(data_contract, server="bigquery"))

    assert result == yaml.safe_load(expected_dbt_model)


def test_to_dbt_models_with_no_model_type():
    data_contract = DataContractSpecification.from_file("fixtures/export/datacontract_no_model_type.yaml")
    expected_dbt_model = """
version: 2
models:
- name: orders
  config:
    meta:
      data_contract: orders-unit-test
      owner: checkout
  description: The orders model
  columns:
  - name: order_id
    data_tests:
    - not_null
    - unique
    - dbt_expectations.expect_column_value_lengths_to_be_between:
        min_value: 8
        max_value: 10
    - dbt_expectations.expect_column_values_to_match_regex:
        regex: ^B[0-9]+$
    data_type: VARCHAR
    meta:
      pii: true
      classification: sensitive
    tags:
    - order_id
  - name: order_total
    data_tests:
    - not_null
    - dbt_expectations.expect_column_values_to_be_between:
        min_value: 0
        max_value: 1000000
    data_type: NUMBER
    description: The order_total field
  - name: order_status
    data_tests:
    - not_null
    - accepted_values:
        values:
        - pending
        - shipped
        - delivered
    data_type: TEXT
"""

    result = yaml.safe_load(to_dbt_models_yaml(data_contract))

    assert result == yaml.safe_load(expected_dbt_model)


def read_file(file):
    if not os.path.exists(file):
        print(f"The file '{file}' does not exist.")
        sys.exit(1)
    with open(file, "r") as file:
        file_content = file.read()
    return file_content
