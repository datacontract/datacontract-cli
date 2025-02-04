import os
import sys

import yaml
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.export.odcs_v3_exporter import to_odcs_v3_yaml
from datacontract.model.data_contract_specification import DataContractSpecification

# logging.basicConfig(level=logging.DEBUG, force=True)


def test_cli():
    runner = CliRunner()
    result = runner.invoke(app, ["export", "./fixtures/export/datacontract.yaml", "--format", "odcs_v3"])
    assert result.exit_code == 0


def test_to_odcs():
    data_contract = DataContractSpecification.from_string(read_file("fixtures/export/datacontract.yaml"))
    expected_odcs_model = """
apiVersion: v3.0.0
kind: DataContract
id: orders-unit-test
name: Orders Unit Test
version: 1.0.0
domain: checkout
status: active
description:
  purpose: null
  limitations: Not intended to use in production
  usage: This data contract serves to demo datacontract CLI export.

schema:
  - name: orders
    physicalName: orders
    logicalType: object
    physicalType: table
    description: The orders model
    properties:
      - name: order_id
        businessName: Order ID
        logicalType: string
        logicalTypeOptions:
            minLength: 8
            maxLength: 10
            pattern: ^B[0-9]+$
        physicalType: varchar
        isNullable: false
        isUnique: true       
        tags: 
          - "order_id"
        classification: sensitive
        examples:
        - B12345678
        - B12345679
        customProperties:
        - property: customFieldProperty1
          value: customFieldProperty1Value
        - property: pii
          value: true
      - name: order_total
        logicalType: integer
        logicalTypeOptions:
            minimum: 0
            maximum: 1000000
        physicalType: bigint
        isNullable: false
        description: The order_total field
        quality:
          - type: sql
            description: 95% of all order total values are expected to be between 10 and 499 EUR.
            query: |
              SELECT quantile_cont(order_total, 0.95) AS percentile_95
              FROM orders
            mustBeBetween: [1000, 49900]
      - name: order_status
        logicalType: string
        physicalType: text
        isNullable: false
    quality:
    - type: sql
      description: Row Count
      query: |
        SELECT COUNT(*) AS row_count
        FROM orders
      mustBeGreaterThan: 1000  
    customProperties:
    - property: customModelProperty1
      value: customModelProperty1Value
servers:
  - server: production
    type: snowflake
    environment: production
    account: my-account
    database: my-database
    schema: my-schema
    roles:
      - name: analyst_us
        description: Access to the data for US region

support:
  - channel: email
    url: mailto:team-orders@example.com
  - channel: other
    url: https://wiki.example.com/teams/checkout

customProperties:
- property: otherField
  value: otherValue
"""

    odcs = to_odcs_v3_yaml(data_contract)

    assert yaml.safe_load(odcs) == yaml.safe_load(expected_odcs_model)


def read_file(file):
    if not os.path.exists(file):
        print(f"The file '{file}' does not exist.")
        sys.exit(1)
    with open(file, "r") as file:
        file_content = file.read()
    return file_content
