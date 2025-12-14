import os
import sys

import yaml
from open_data_contract_standard.model import OpenDataContractStandard, SchemaObject, SchemaProperty
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.export.dbt_exporter import to_dbt_models_yaml

# logging.basicConfig(level=logging.DEBUG, force=True)


def test_cli():
    runner = CliRunner()
    result = runner.invoke(app, ["export", "./fixtures/export/datacontract.odcs.yaml", "--format", "dbt"])
    assert result.exit_code == 0


def test_to_dbt_models():
    data_contract = OpenDataContractStandard.from_file("fixtures/export/datacontract.odcs.yaml")
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
    data_tests:
      - dbt_utils.unique_combination_of_columns:
          combination_of_columns:
            - order_id
            - order_status
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
    odcs = OpenDataContractStandard.from_file("fixtures/export/datacontract.odcs.yaml")
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
    data_tests:
      - dbt_utils.unique_combination_of_columns:
          combination_of_columns:
            - order_id
            - order_status
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

    result = yaml.safe_load(to_dbt_models_yaml(odcs, server="bigquery"))

    assert result == yaml.safe_load(expected_dbt_model)



def test_to_dbt_models_with_model_level_composite_primary_key():
    """Test model-level primaryKey with multiple columns generates dbt_utils.unique_combination_of_columns"""
    # Create test data with model-level composite primaryKey using ODCS
    data_contract = OpenDataContractStandard(
        apiVersion="v3.1.0",
        kind="DataContract",
        id="my-data-contract-id",
        schema=[
            SchemaObject(
                name="test_table",
                physicalType="table",
                properties=[
                    SchemaProperty(name="order_id", logicalType="string", required=True, primaryKey=True, primaryKeyPosition=1),
                    SchemaProperty(name="user_id", logicalType="string", required=True, primaryKey=True, primaryKeyPosition=2),
                    SchemaProperty(name="product_id", logicalType="string", required=True),
                ],
            )
        ],
    )

    expected_dbt_model = """
version: 2
models:
  - name: test_table
    config:
      meta:
        data_contract: my-data-contract-id
      materialized: table
      contract:
        enforced: true
    data_tests:
      - dbt_utils.unique_combination_of_columns:
          combination_of_columns:
            - order_id
            - user_id
    columns:
      - name: order_id
        data_type: STRING
        constraints:
          - type: not_null
      - name: user_id
        data_type: STRING
        constraints:
          - type: not_null
      - name: product_id
        data_type: STRING
        constraints:
          - type: not_null
"""

    result = yaml.safe_load(to_dbt_models_yaml(data_contract))
    expected = yaml.safe_load(expected_dbt_model)

    assert result == expected


def test_to_dbt_models_with_single_column_primary_key():
    """Test model-level primaryKey with single column adds unique constraint to column"""
    # Create test data with model-level single primaryKey using ODCS
    data_contract = OpenDataContractStandard(
        apiVersion="v3.1.0",
        kind="DataContract",
        id="my-data-contract-id",
        schema=[
            SchemaObject(
                name="test_table",
                physicalType="table",
                properties=[
                    SchemaProperty(name="order_id", logicalType="string", required=True, primaryKey=True, primaryKeyPosition=1),
                    SchemaProperty(name="user_id", logicalType="string", required=True),
                    SchemaProperty(name="product_id", logicalType="string", required=True),
                ],
            )
        ],
    )

    expected_dbt_model = """
version: 2
models:
  - name: test_table
    config:
      meta:
        data_contract: my-data-contract-id
      materialized: table
      contract:
        enforced: true
    columns:
      - name: order_id
        data_type: STRING
        constraints:
          - type: not_null
          - type: unique
      - name: user_id
        data_type: STRING
        constraints:
          - type: not_null
      - name: product_id
        data_type: STRING
        constraints:
          - type: not_null
"""

    result = yaml.safe_load(to_dbt_models_yaml(data_contract))
    expected = yaml.safe_load(expected_dbt_model)

    assert result == expected


def read_file(file):
    if not os.path.exists(file):
        print(f"The file '{file}' does not exist.")
        sys.exit(1)
    with open(file, "r") as file:
        file_content = file.read()
    return file_content
