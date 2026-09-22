"""A quality rule the CLI cannot run is reported, not dropped."""

from datacontract.data_contract import DataContract
from datacontract.engines.checks.create_checks import create_checks
from datacontract.model.run import ResultEnum

CSV_PATH = "./fixtures/diagnostics/data/orders.csv"


def _odcs(model_quality: str = "", property_quality: str = "") -> str:
    return f"""
apiVersion: v3.1.0
kind: DataContract
id: unrunnable_rules_test
version: 1.0.0
status: active
servers:
  - server: local
    type: local
    path: {CSV_PATH}
    format: csv
schema:
  - name: orders
    properties:
      - name: amount
        logicalType: integer
{property_quality}
{model_quality}
"""


def _checks(contract_str: str):
    odcs = DataContract(data_contract_str=contract_str).get_data_contract()
    return create_checks(odcs, odcs.servers[0])


def test_property_metric_declared_on_a_schema_warns():
    checks = _checks(
        _odcs(
            model_quality="""    quality:
      - type: library
        metric: nullValues
        mustBe: 0
"""
        )
    )
    assert not any(c.type == "field_null_values" for c in checks)
    spec = next(c for c in checks if c.type == "model_quality_library")
    assert spec.preset_result == "warning"
    assert "only supported at property level" in spec.preset_reason


def test_row_count_on_a_property_warns_instead_of_checking_the_table():
    # A table-level row count here would be a green check answering a question nobody asked.
    checks = _checks(
        _odcs(
            property_quality="""        quality:
          - type: library
            metric: rowCount
            mustBeGreaterThan: 0
"""
        )
    )
    assert not any(c.type == "row_count" for c in checks)
    spec = next(c for c in checks if c.type == "field_quality_library")
    assert spec.preset_result == "warning"
    assert "only supported at schema level" in spec.preset_reason


def test_the_rule_stays_selectable_by_quality_id():
    checks = _checks(
        _odcs(
            model_quality="""    quality:
      - id: no-nulls
        type: library
        metric: nullValues
        mustBe: 0
"""
        )
    )
    spec = next(c for c in checks if c.type == "model_quality_library")
    assert spec.quality_id == "no-nulls"


def test_test_reports_the_warning_and_still_exits_without_failing():
    run = DataContract(
        data_contract_str=_odcs(
            model_quality="""    quality:
      - type: library
        metric: nullValues
        mustBe: 0
"""
        )
    ).test()

    assert run.result == ResultEnum.warning
    assert any(c.result == ResultEnum.warning for c in run.checks)


def test_dry_run_keeps_the_warning_instead_of_skipping_it():
    run = DataContract(
        data_contract_str=_odcs(
            model_quality="""    quality:
      - type: library
        metric: nullValues
        mustBe: 0
"""
        ),
        dry_run=True,
    ).test()

    warning = next(c for c in run.checks if c.result == ResultEnum.warning)
    assert "only supported at property level" in warning.reason
    assert run.result == ResultEnum.warning


def test_lint_warns_about_a_rule_that_could_never_be_tested():
    run = DataContract(
        data_contract_str=_odcs(
            property_quality="""        quality:
          - type: library
            metric: invalidValues
            mustBe: 0
"""
        )
    ).lint()

    assert run.result == ResultEnum.warning
    warning = next(c for c in run.checks if c.result == ResultEnum.warning)
    assert warning.field == "amount"
    assert "validValues or a pattern" in warning.reason


def test_lint_stays_green_for_a_runnable_rule():
    run = DataContract(
        data_contract_str=_odcs(
            property_quality="""        quality:
          - type: library
            metric: nullValues
            mustBe: 0
"""
        )
    ).lint()

    assert run.result == ResultEnum.passed


def test_lint_reaches_rules_on_nested_and_array_item_properties():
    run = DataContract(
        data_contract_str="""
apiVersion: v3.1.0
kind: DataContract
id: nested_unrunnable_rules_test
version: 1.0.0
status: active
schema:
  - name: orders
    properties:
      - name: tags
        logicalType: array
        items:
          logicalType: object
          properties:
            - name: label
              logicalType: string
              quality:
                - type: library
                  metric: invalidValues
                  mustBe: 0
      - name: meta
        logicalType: object
        properties:
          - name: source
            logicalType: string
            quality:
              - type: library
                metric: rowCount
                mustBe: 1
"""
    ).lint()

    fields = {c.field for c in run.checks if c.result == ResultEnum.warning}
    assert fields == {"tags[].label", "meta.source"}
