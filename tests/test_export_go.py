from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract

# logging.basicConfig(level=logging.DEBUG, force=True)


def test_cli():
    runner = CliRunner()
    result = runner.invoke(app, ["export", "go", "./fixtures/export/datacontract.odcs.yaml"])
    assert result.exit_code == 0


def test_to_go_types():
    actual = DataContract(data_contract_file="fixtures/export/datacontract.odcs.yaml").export("go")
    expected = """
package main


type Orders struct {
    OrderId string `json:"order_id" avro:"order_id"`
    OrderTotal int64 `json:"order_total" avro:"order_total"`  // The order_total field
    OrderStatus string `json:"order_status" avro:"order_status"`
}

"""
    assert actual.strip() == expected.strip()


def test_to_go_types_imports_time():
    actual = DataContract(
        data_contract_str="""
apiVersion: v3.1.0
kind: DataContract
id: go-time
name: Go Time
version: 1.0.0
status: active
schema:
- name: orders
  properties:
  - name: order_id
    logicalType: string
    required: true
  - name: order_timestamp
    logicalType: timestamp
    physicalType: timestamp
    required: true
  - name: delivery_date
    logicalType: date
"""
    ).export("go")
    expected = """
package main

import "time"


type Orders struct {
    OrderId string `json:"order_id" avro:"order_id"`
    OrderTimestamp time.Time `json:"order_timestamp" avro:"order_timestamp"`
    DeliveryDate *time.Time `json:"delivery_date,omitempty" avro:"delivery_date"`
}

"""
    assert actual.strip() == expected.strip()
