"""Tests for `datacontract test --include-failed-samples`.

Runs the ibis engine in-process against a small local CSV via duckdb, so no
database container is needed. The fixture (fixtures/failed_samples/orders.csv)
has, by design:
  - id: declared unique; value 2 appears twice  -> duplicate
  - email: PII (classification), pattern ^.+@.+$; 6 rows fail -> exercises the limit
  - amount: range [0, 100]; 200 is out of range  -> invalid
  - region: required; 2 rows are empty           -> missing
"""

from datacontract.data_contract import DataContract
from datacontract.model.run import ResultEnum

CSV_PATH = "./fixtures/failed_samples/orders.csv"

CONTRACT = f"""
apiVersion: v3.0.2
kind: DataContract
id: failed_samples_test
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
      - name: id
        logicalType: integer
        unique: true
      - name: email
        logicalType: string
        classification: PII
        logicalTypeOptions:
          pattern: "^.+@.+$"
      - name: amount
        logicalType: integer
        logicalTypeOptions:
          minimum: 0
          maximum: 100
      - name: region
        logicalType: string
        required: true
"""


def _run(include_failed_samples: bool):
    return DataContract(data_contract_str=CONTRACT, include_failed_samples=include_failed_samples).test()


def _check(run, type_, field=None):
    return next(c for c in run.checks if c.type == type_ and (field is None or c.field == field))


def test_no_samples_collected_without_flag():
    run = _run(include_failed_samples=False)
    assert run.result == ResultEnum.failed  # there are real violations
    assert all(c.failed_samples is None for c in run.checks)


def test_missing_samples_have_identifier_and_offending_column():
    run = _run(include_failed_samples=True)
    check = _check(run, "field_required", field="region")
    assert check.result == ResultEnum.failed
    assert check.failed_samples is not None
    # region is empty for ids 3 and 5.
    assert {s["id"] for s in check.failed_samples} == {3, 5}
    for s in check.failed_samples:
        assert set(s.keys()) == {"id", "region"}
        assert s["region"] is None


def test_invalid_range_sample_includes_offending_value():
    run = _run(include_failed_samples=True)
    check = _check(run, "field_maximum", field="amount")
    assert check.result == ResultEnum.failed
    assert check.failed_samples == [{"id": 3, "amount": 200}]


def test_samples_respect_the_limit():
    run = _run(include_failed_samples=True)
    check = _check(run, "field_regex", field="email")
    assert check.result == ResultEnum.failed
    # 6 rows fail the email pattern, but samples are capped at 5.
    assert len(check.failed_samples) == 5


def test_sensitive_column_is_omitted_from_samples():
    run = _run(include_failed_samples=True)
    check = _check(run, "field_regex", field="email")
    # email is classified PII, so its value must not appear; only the identifier.
    for s in check.failed_samples:
        assert "email" not in s
        assert set(s.keys()) == {"id"}


def test_duplicate_samples_report_key_and_count():
    run = _run(include_failed_samples=True)
    check = _check(run, "field_unique", field="id")
    assert check.result == ResultEnum.failed
    assert check.failed_samples == [{"id": 2, "duplicate_count": 2}]
