"""Tests for ODCS quality `unit: percent` thresholds and `severity` handling.

Unit tests cover the engine-neutral check IR (``create_checks``); the end-to-end
tests run the ibis engine in-process against a small local CSV via duckdb, so
they need no database container.
"""

from datacontract.data_contract import DataContract
from datacontract.engines.checks.check_spec import MetricType
from datacontract.engines.checks.create_checks import create_checks
from datacontract.model.run import ResultEnum

# fixtures/diagnostics/data/orders.csv (shared, see test_diagnostics fixture):
#   order_id,email,amount
#   1,alice@example.com,50
#   2,bob@test.com,10
#   3,no-at-sign,200
#   4,verylongaddress@example.com,-5
#   2,carol@test.com,30
# => 5 rows; amount has 2 values (200, -5) outside [10, 30, 50] => 40% invalid.
CSV_PATH = "./fixtures/diagnostics/data/orders.csv"


def _odcs(amount_quality: str = "", email_quality: str = "", model_quality: str = "") -> str:
    return f"""
apiVersion: v3.0.2
kind: DataContract
id: percent_severity_test
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
      - name: email
        logicalType: string
{email_quality}
      - name: amount
        logicalType: integer
{amount_quality}
{model_quality}
"""


def _checks(contract_str: str):
    dc = DataContract(data_contract_str=contract_str)
    odcs = dc.get_data_contract()
    server = odcs.servers[0]
    return create_checks(odcs, server)


def _find(checks, type_):
    return next(c for c in checks if c.type == type_)


# ---------------------------------------------------------------------------
# unit tests: create_checks wires unit/severity onto the CheckSpec IR
# ---------------------------------------------------------------------------
def test_create_checks_sets_percent_and_severity():
    contract = _odcs(
        amount_quality="""        quality:
          - type: library
            metric: invalidValues
            unit: percent
            severity: warning
            mustBeLessThan: 10
            arguments:
              validValues: [10, 30, 50]
"""
    )
    spec = _find(_checks(contract), "field_invalid_values")
    assert spec.metric == MetricType.INVALID_COUNT
    assert spec.threshold_is_percent is True
    assert spec.severity == "warning"


def test_create_checks_defaults_to_count_and_no_severity():
    contract = _odcs(
        amount_quality="""        quality:
          - type: library
            metric: invalidValues
            mustBe: 0
            arguments:
              validValues: [10, 30, 50]
"""
    )
    spec = _find(_checks(contract), "field_invalid_values")
    assert spec.threshold_is_percent is False
    assert spec.severity is None


def test_create_checks_percent_ignored_for_rowcount(caplog):
    # rowCount has no row-fraction meaning; percent must not silently apply.
    contract = _odcs(
        model_quality="""    quality:
      - type: library
        metric: rowCount
        unit: percent
        mustBeGreaterThan: 10
"""
    )
    spec = _find(_checks(contract), "row_count")
    assert spec.threshold_is_percent is False
    assert "does not support unit: percent" in caplog.text


# ---------------------------------------------------------------------------
# end-to-end tests: ibis engine against local CSV (duckdb, in-process)
# ---------------------------------------------------------------------------
def _quality_check(run, type_):
    return next(c for c in run.checks if c.type == type_)


def test_percent_threshold_passes():
    # 0% of emails are null, threshold < 50% => pass.
    contract = _odcs(
        email_quality="""        quality:
          - type: library
            metric: nullValues
            unit: percent
            mustBeLessThan: 50
"""
    )
    run = DataContract(data_contract_str=contract).test()
    check = _quality_check(run, "field_null_values")
    assert check.result == ResultEnum.passed
    assert check.diagnostics["unit"] == "percent"
    assert check.diagnostics["percent"] == 0.0


def test_percent_threshold_fails_hard_without_severity():
    # 40% of amounts are invalid, threshold < 10%, no severity => hard failure.
    contract = _odcs(
        amount_quality="""        quality:
          - type: library
            metric: invalidValues
            unit: percent
            mustBeLessThan: 10
            arguments:
              validValues: [10, 30, 50]
"""
    )
    run = DataContract(data_contract_str=contract).test()
    check = _quality_check(run, "field_invalid_values")
    assert check.result == ResultEnum.failed
    assert check.diagnostics["percent"] == 40.0
    assert "40.0% (2 of 5 rows)" in check.reason
    assert "< 10%" in check.reason
    assert run.result == ResultEnum.failed


def test_severity_warning_downgrades_percent_failure():
    # Same 40% > 10% violation, but severity: warning => warning, run not failed.
    contract = _odcs(
        amount_quality="""        quality:
          - type: library
            metric: invalidValues
            unit: percent
            severity: warning
            mustBeLessThan: 10
            arguments:
              validValues: [10, 30, 50]
"""
    )
    run = DataContract(data_contract_str=contract).test()
    check = _quality_check(run, "field_invalid_values")
    assert check.result == ResultEnum.warning
    assert check.diagnostics["severity"] == "warning"
    # No hard failures elsewhere => the run is a warning, not a failure.
    assert run.result == ResultEnum.warning


def test_severity_warning_on_absolute_count_check():
    # Severity also applies to plain (non-percent) count thresholds.
    contract = _odcs(
        amount_quality="""        quality:
          - type: library
            metric: invalidValues
            severity: warning
            mustBe: 0
            arguments:
              validValues: [10, 30, 50]
"""
    )
    run = DataContract(data_contract_str=contract).test()
    check = _quality_check(run, "field_invalid_values")
    assert check.result == ResultEnum.warning
    assert run.result == ResultEnum.warning


def test_invalid_values_pattern_argument_runs_regex():
    # 1 of 5 emails ("no-at-sign") lacks an @ => 20% invalid, threshold < 10% => fail.
    contract = _odcs(
        email_quality="""        quality:
          - type: library
            metric: invalidValues
            unit: percent
            mustBeLessThan: 10
            arguments:
              pattern: '@'
"""
    )
    run = DataContract(data_contract_str=contract).test()
    check = _quality_check(run, "field_invalid_values")
    assert check.result == ResultEnum.failed
    assert check.diagnostics["percent"] == 20.0
    assert "20.0% (1 of 5 rows)" in check.reason


def test_invalid_values_without_arguments_is_skipped(caplog):
    # An invalidValues check with neither validValues nor pattern can never fail, therefore it should be dropped
    contract = _odcs(
        email_quality="""        quality:
          - type: library
            metric: invalidValues
            mustBe: 0
"""
    )
    checks = _checks(contract)
    assert not any(c.type == "field_invalid_values" for c in checks)
    assert "no validValues or pattern argument" in caplog.text
