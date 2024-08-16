import yaml
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.export.dbt_converter import to_dbt_sources_yaml
from datacontract.model.data_contract_specification import DataContractSpecification

# logging.basicConfig(level=logging.DEBUG, force=True)


def test_cli():
    runner = CliRunner()
    result = runner.invoke(
        app, ["export", "./fixtures/export/datacontract.yaml", "--format", "dbt-sources", "--server", "production"]
    )
    print(result.stdout)
    assert result.exit_code == 0


def test_to_dbt_sources():
    data_contract = DataContractSpecification.from_file("fixtures/export/datacontract.yaml")
    expected_dbt_model = """
version: 2
sources:
  - name: orders-unit-test
    description: The orders data contract  
    database: my-database
    schema: my-schema  
    meta:
      owner: checkout
    tables:
      - name: orders 
        description: The orders model
        columns:
          - name: order_id
            tests:
              - dbt_expectations.dbt_expectations.expect_column_values_to_be_of_type:
                  column_type: VARCHAR
              - not_null
              - unique
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
            description: The order_total field
            tests:
              - dbt_expectations.dbt_expectations.expect_column_values_to_be_of_type:
                  column_type: NUMBER
              - not_null
              - dbt_expectations.expect_column_values_to_be_between:
                   min_value: 0
                   max_value: 1000000
          - name: order_status
            tests:
              - dbt_expectations.dbt_expectations.expect_column_values_to_be_of_type:
                  column_type: TEXT
              - not_null
              - accepted_values:
                  values:
                    - 'pending'
                    - 'shipped'
                    - 'delivered'
"""

    result = to_dbt_sources_yaml(data_contract, "production")

    assert yaml.safe_load(result) == yaml.safe_load(expected_dbt_model)
