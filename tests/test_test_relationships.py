"""`relationships` with type foreignKey: every non-null key must exist in the referenced schema."""

from datacontract.data_contract import DataContract
from datacontract.model.run import ResultEnum

SERVER = """apiVersion: v3.1.0
kind: DataContract
id: relationships
name: relationships
version: 1.0.0
status: active
servers:
  - server: local
    type: local
    format: csv
    path: {path}/{{model}}.csv
"""

ORDERS = """schema:
  - name: orders
    properties:
      - name: order_id
        logicalType: string
        primaryKey: true
  - name: line_items
    properties:
      - name: line_item_id
        logicalType: string
        primaryKey: true
      - name: order_id
        logicalType: string
        relationships:
          - type: foreignKey
            to: orders.order_id
"""


def _write(tmp_path, **tables):
    for name, rows in tables.items():
        (tmp_path / f"{name}.csv").write_text("\n".join(rows) + "\n")


def _relationship_checks(tmp_path, schema, schema_name="all"):
    contract = SERVER.format(path=tmp_path) + schema
    run = DataContract(data_contract_str=contract, schema_name=schema_name).test()
    return [c for c in run.checks if c.type == "field_relationship"]


def test_orphaned_key_fails(tmp_path):
    _write(
        tmp_path,
        orders=["order_id", "o1", "o2"],
        line_items=["line_item_id,order_id", "l1,o1", "l2,o2", "l3,o999"],
    )

    [check] = _relationship_checks(tmp_path, ORDERS)

    assert check.result == ResultEnum.failed
    assert check.model == "line_items"
    assert check.field == "order_id"
    assert check.dimension == "consistency"
    assert "was 1" in check.reason


def test_null_keys_and_matching_keys_pass(tmp_path):
    _write(
        tmp_path,
        orders=["order_id", "o1", "o2"],
        line_items=["line_item_id,order_id", "l1,o1", "l2,o2", "l3,"],
    )

    [check] = _relationship_checks(tmp_path, ORDERS)

    assert check.result == ResultEnum.passed


def test_composite_key_declared_on_the_schema(tmp_path):
    _write(
        tmp_path,
        order_lines=["order_id,line_no", "o1,1", "o1,2"],
        shipments=["shipment_id,order_id,line_no", "s1,o1,1", "s2,o1,3"],
    )
    schema = """schema:
  - name: order_lines
    properties:
      - name: order_id
        logicalType: string
      - name: line_no
        logicalType: integer
  - name: shipments
    properties:
      - name: shipment_id
        logicalType: string
      - name: order_id
        logicalType: string
      - name: line_no
        logicalType: integer
    relationships:
      - type: foreignKey
        from: [shipments.order_id, shipments.line_no]
        to: [order_lines.order_id, order_lines.line_no]
"""

    [check] = _relationship_checks(tmp_path, schema)

    # (o1, 3) matches neither line, although o1 and 3 each occur on their own
    assert check.result == ResultEnum.failed
    assert check.field is None
    assert "was 1" in check.reason


def test_self_reference(tmp_path):
    _write(tmp_path, employees=["employee_id,manager_id", "e1,", "e2,e1", "e3,e9"])
    schema = """schema:
  - name: employees
    properties:
      - name: employee_id
        logicalType: string
      - name: manager_id
        logicalType: string
        relationships:
          - type: foreignKey
            to: employees.employee_id
"""

    [check] = _relationship_checks(tmp_path, schema)

    assert check.result == ResultEnum.failed
    assert "was 1" in check.reason


def test_unknown_target_is_a_warning(tmp_path):
    _write(tmp_path, line_items=["line_item_id,order_id", "l1,o1"])
    schema = """schema:
  - name: line_items
    properties:
      - name: line_item_id
        logicalType: string
      - name: order_id
        logicalType: string
        relationships:
          - type: foreignKey
            to: order.order_id
"""

    [check] = _relationship_checks(tmp_path, schema)

    assert check.result == ResultEnum.warning
    assert "order.order_id" in check.reason


def test_referenced_schema_outside_the_tested_one_is_a_warning(tmp_path):
    _write(
        tmp_path,
        orders=["order_id", "o1"],
        line_items=["line_item_id,order_id", "l1,o1"],
    )

    [check] = _relationship_checks(tmp_path, ORDERS, schema_name="line_items")

    assert check.result == ResultEnum.warning
    assert "orders" in check.reason
