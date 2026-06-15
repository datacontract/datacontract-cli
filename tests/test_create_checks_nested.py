from open_data_contract_standard.model import Server

from datacontract.data_contract import DataContract
from datacontract.engines.checks.check_spec import MetricType
from datacontract.engines.checks.create_checks import create_checks

CONTRACT = """
apiVersion: v3.0.2
kind: DataContract
id: nested-checks
version: 1.0.0
status: active
schema:
  - name: orders
    properties:
      - name: id
        logicalType: string
        required: true
      - name: user
        logicalType: object
        properties:
          - name: email
            logicalType: string
            required: true
            logicalTypeOptions:
              pattern: ^.+@.+$
          - name: status
            logicalType: string
            quality:
              - type: sql
                query: SELECT COUNT(*) FROM {model} WHERE {field} NOT IN ('active', 'inactive')
                mustBe: 0
      - name: line_items
        logicalType: array
        items:
          logicalType: object
          properties:
            - name: sku
              logicalType: string
              required: true
"""


def _checks(server_type: str):
    odcs = DataContract(data_contract_str=CONTRACT).get_data_contract()
    return create_checks(odcs, Server(type=server_type))


def test_create_checks_recurses_for_dataframe_nested_structs_and_arrays():
    checks = _checks("dataframe")

    assert any(c.field == "user.email" and c.type == "field_required" and c.model == "orders" for c in checks)
    assert any(c.field == "user.email" and c.type == "field_regex" and c.model == "orders" for c in checks)
    assert any(c.field == "sku" and c.type == "field_required" and c.model == "orders__line_items" for c in checks)

    nested_sql = next(c for c in checks if c.type == "field_quality_sql")
    assert nested_sql.field == "user.status"
    assert nested_sql.model == "orders"
    assert nested_sql.metric == MetricType.CUSTOM_SQL
    assert "user.status" in (nested_sql.query or "")


def test_create_checks_skips_nested_checks_for_unverified_backends():
    checks = _checks("postgres")

    assert not any(c.field == "user.email" for c in checks)
    assert not any(c.model == "orders__line_items" for c in checks)
