import os
import sys

import yaml
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.export.odcs_v2_exporter import to_odcs_v2_yaml
from datacontract.model.data_contract_specification import DataContractSpecification

# logging.basicConfig(level=logging.DEBUG, force=True)


def test_cli():
    runner = CliRunner()
    result = runner.invoke(app, ["export", "./fixtures/export/datacontract.yaml", "--format", "odcs_v2"])
    assert result.exit_code == 0


def test_to_odcs():
    data_contract = DataContractSpecification.from_string(read_file("fixtures/export/datacontract.yaml"))
    expected_odcs_model = """
kind: DataContract
apiVersion: 2.3.0
uuid: orders-unit-test
version: 1.0.0
datasetDomain: checkout 
quantumName: Orders Unit Test
status: unknown
description:
  purpose: null
  limitations: Not intended to use in production
  usage: This data contract serves to demo datacontract CLI export.
productDl: team-orders@example.com
productFeedbackUrl: https://wiki.example.com/teams/checkout

type: tables

dataset:
  - table: orders
    physicalName: orders
    description: The orders model
    columns:
      - column: order_id
        logicalType: varchar
        physicalType: varchar
        isNullable: false
        isUnique: true
        tags: 
          - "order_id"
          - "pii:true"
          - "minLength:8"
          - "maxLength:10"
          - "pattern:^B[0-9]+$"
        classification: sensitive
      - column: order_total
        logicalType: bigint
        physicalType: bigint
        isNullable: false
        description: The order_total field
        tags: 
          - minimum:0
          - maximum:1000000
      - column: order_status
        logicalType: text
        physicalType: text
        isNullable: false
"""

    odcs = to_odcs_v2_yaml(data_contract)

    assert yaml.safe_load(odcs) == yaml.safe_load(expected_odcs_model)


def read_file(file):
    if not os.path.exists(file):
        print(f"The file '{file}' does not exist.")
        sys.exit(1)
    with open(file, "r") as file:
        file_content = file.read()
    return file_content
