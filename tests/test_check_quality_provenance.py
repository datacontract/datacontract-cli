"""What a check records about the contract element it was derived from."""

from open_data_contract_standard.model import OpenDataContractStandard

from datacontract.engines.checks.create_checks import create_checks
from datacontract.engines.ibis.ibis_check_execute import build_check_stubs

CONTRACT = """
apiVersion: v3.0.2
kind: DataContract
id: quality_provenance
version: 1.0.0
status: active
servers:
  - server: local
    type: local
    path: ./fixtures/diagnostics/data/orders.csv
    format: csv
slaProperties:
  - id: freshness-sla
    property: freshness
    element: orders.processed_timestamp
    value: 3650
    unit: d
schema:
  - name: orders
    properties:
      - name: order_id
        logicalType: integer
        required: true
        quality:
          - id: order_id_is_unique
            description: order_id identifies an order.
            type: library
            metric: duplicateValues
            dimension: uniqueness
            mustBe: 0
      - name: processed_timestamp
        logicalType: date
"""


def _stubs():
    data_contract = OpenDataContractStandard.from_string(CONTRACT)
    checks = build_check_stubs(create_checks(data_contract, data_contract.servers[0]))
    return {check.type: check for check in checks}


def test_a_check_from_a_quality_rule_carries_the_rule_it_came_from():
    check = _stubs()["field_duplicate_values"]

    assert check.qualityId == "order_id_is_unique"
    assert check.dimension == "uniqueness"
    assert check.qualityDefinition == (
        "id: order_id_is_unique\n"
        "description: order_id identifies an order.\n"
        "dimension: uniqueness\n"
        "type: library\n"
        "metric: duplicateValues\n"
        "mustBe: 0\n"
    )


def test_a_schema_check_carries_the_dimension_it_measures_but_no_rule():
    check = _stubs()["field_required"]

    assert check.dimension == "completeness"
    assert check.qualityDefinition is None
    assert check.qualityId is None


def test_a_service_level_check_is_identified_by_its_sla_property_id():
    check = _stubs()["servicelevel_freshness"]

    assert check.qualityId == "freshness-sla"
    assert check.dimension == "timeliness"
    assert check.qualityDefinition is None
