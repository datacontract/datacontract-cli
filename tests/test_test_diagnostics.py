"""Diagnostics produced by the ibis check engine.

Each executed check carries a structured ``diagnostics`` dict explaining why it
passed/failed: the metric, measured value, threshold, and (for "bad row"
metrics) the total row count and failed fraction. invalid_count checks also
report the validity rule they enforced.
"""

import ibis
import pandas as pd

from datacontract.data_contract import DataContract
from datacontract.engines.checks.check_spec import CheckSpec, MetricType
from datacontract.engines.ibis.ibis_check_execute import _run_freshness, _run_type, build_check_stubs
from datacontract.model.run import ResultEnum, Run


def _find(run, type_, field):
    return next(c for c in run.checks if c.type == type_ and c.field == field)


def test_diagnostics_invalid_count_failed_fraction_and_constraint():
    run = DataContract(data_contract_file="fixtures/diagnostics/datacontract.yaml").test()

    # email maxLength 20: one of five rows is too long.
    max_length = _find(run, "field_max_length", "email")
    assert max_length.result == ResultEnum.failed
    assert max_length.diagnostics == {
        "metric": "invalid_count",
        "field": "email",
        "value": 1,
        "threshold": "= 0",
        "row_count": 5,
        "failed_fraction": 0.2,
        "constraint": {"max_length": 20},
    }

    # email pattern: one row has no "@".
    regex = _find(run, "field_regex", "email")
    assert regex.result == ResultEnum.failed
    assert regex.diagnostics["constraint"] == {"pattern": "^.+@.+$"}
    assert regex.diagnostics["failed_fraction"] == 0.2

    # amount minimum 0: one negative value.
    minimum = _find(run, "field_minimum", "amount")
    assert minimum.result == ResultEnum.failed
    assert minimum.diagnostics["constraint"] == {"minimum": 0}


def test_diagnostics_passing_check_reports_zero_fraction():
    run = DataContract(data_contract_file="fixtures/diagnostics/datacontract.yaml").test()
    required = _find(run, "field_required", "email")
    assert required.result == ResultEnum.passed
    assert required.diagnostics["metric"] == "missing_count"
    assert required.diagnostics["value"] == 0
    assert required.diagnostics["row_count"] == 5
    assert required.diagnostics["failed_fraction"] == 0.0


def test_diagnostics_duplicate_and_present():
    run = DataContract(data_contract_file="fixtures/diagnostics/datacontract.yaml").test()

    unique = _find(run, "field_unique", "order_id")
    assert unique.result == ResultEnum.failed
    assert unique.diagnostics == {
        "metric": "duplicate_count",
        "field": "order_id",
        "value": 1,
        "threshold": "= 0",
    }

    present = _find(run, "field_is_present", "order_id")
    assert present.diagnostics == {"metric": "field_present", "field": "order_id", "present": True}


def _run_with(specs):
    run = Run.create_run()
    run.checks = build_check_stubs(specs)
    return run


def test_diagnostics_field_type_mismatch():
    t = ibis.memtable(pd.DataFrame({"amount": ["not-a-number"]}))
    spec = CheckSpec(
        key="k",
        category="schema",
        type="field_type",
        name="type of amount",
        model="m",
        metric=MetricType.FIELD_TYPE,
        field="amount",
        expected_category="number",
        expected_type_label="integer",
    )
    run = _run_with([spec])

    _run_type(run, t.schema(), {c.lower(): c for c in t.columns}, spec)

    check = run.checks[0]
    assert check.result == ResultEnum.failed
    assert check.diagnostics["metric"] == "field_type"
    assert check.diagnostics["expected"] == "integer (number)"
    assert "string" in check.diagnostics["actual"]


def test_diagnostics_freshness_exceeded():
    t = ibis.memtable(pd.DataFrame({"ts": [pd.Timestamp("2000-01-01", tz="UTC")]}))
    spec = CheckSpec(
        key="f",
        category="servicelevel",
        type="freshness",
        name="freshness of ts",
        model="m",
        metric=MetricType.FRESHNESS,
        field="ts",
        seconds=3600,
    )
    run = _run_with([spec])

    _run_freshness(run, t, {c.lower(): c for c in t.columns}, spec)

    check = run.checks[0]
    assert check.result == ResultEnum.failed
    assert check.diagnostics["metric"] == "freshness"
    assert check.diagnostics["threshold_seconds"] == 3600
    assert check.diagnostics["age_seconds"] > 3600
    assert "latest_timestamp" in check.diagnostics
