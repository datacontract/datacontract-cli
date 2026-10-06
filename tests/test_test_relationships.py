"""`relationships` with type foreignKey: every non-null key must exist in the referenced schema."""

import pytest

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
    return [c for c in run.checks if c.type == "field_relationships"]


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


def test_one_column_referencing_two_schemas(tmp_path):
    _write(
        tmp_path,
        orders=["order_id", "o1"],
        invoices=["order_id", "o1", "o2"],
        line_items=["line_item_id,order_id", "l1,o1", "l2,o2"],
    )
    schema = """schema:
  - name: orders
    properties:
      - name: order_id
        logicalType: string
  - name: invoices
    properties:
      - name: order_id
        logicalType: string
  - name: line_items
    properties:
      - name: line_item_id
        logicalType: string
      - name: order_id
        logicalType: string
        relationships:
          - type: foreignKey
            to: orders.order_id
          - type: foreignKey
            to: invoices.order_id
"""

    checks = _relationship_checks(tmp_path, schema)

    assert {c.key: c.result for c in checks} == {
        "line_items__order_id__orders__order_id__field_relationships": ResultEnum.failed,
        "line_items__order_id__invoices__order_id__field_relationships": ResultEnum.passed,
    }


def test_physical_names_on_both_sides(tmp_path):
    _write(
        tmp_path,
        orders=["oid", "o1"],
        line_items=["line_item_id,ord", "l1,o1", "l2,o9"],
    )
    schema = """schema:
  - name: orders
    properties:
      - name: order_id
        physicalName: oid
        logicalType: string
  - name: line_items
    properties:
      - name: line_item_id
        logicalType: string
      - name: order_id
        physicalName: ord
        logicalType: string
        relationships:
          - type: foreignKey
            to: orders.order_id
"""

    [check] = _relationship_checks(tmp_path, schema)

    assert check.key == "line_items__ord__orders__oid__field_relationships"
    assert check.result == ResultEnum.failed
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


@pytest.mark.parametrize(
    "to, cause",
    [
        ("order.order_id", "the contract has no schema order"),
        ("line_items.order_idd", "line_items has no property order_idd"),
        ("schema/orders/properties/order_id", "schema/orders/properties/order_id is not a schema.property reference"),
    ],
)
def test_unresolvable_target_is_a_warning_naming_the_cause(tmp_path, to, cause):
    _write(tmp_path, line_items=["line_item_id,order_id", "l1,o1"])
    schema = f"""schema:
  - name: line_items
    properties:
      - name: line_item_id
        logicalType: string
      - name: order_id
        logicalType: string
        relationships:
          - type: foreignKey
            to: {to}
"""

    [check] = _relationship_checks(tmp_path, schema)

    assert check.result == ResultEnum.warning
    assert check.reason == f"The relationship from order_id to {to} is not checked: {cause}."


def test_referenced_schema_outside_the_tested_one_is_a_warning(tmp_path):
    _write(
        tmp_path,
        orders=["order_id", "o1"],
        line_items=["line_item_id,order_id", "l1,o1"],
    )

    [check] = _relationship_checks(tmp_path, ORDERS, schema_name="line_items")

    assert check.result == ResultEnum.warning
    assert check.reason.startswith("Could not read the referenced model 'orders'")
    assert "--schema-name line_items reads only that schema from files" in check.reason
