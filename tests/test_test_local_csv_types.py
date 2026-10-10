"""A CSV value that does not match its column's declared type fails the type check of that column.

The file is read as text; each typed column is converted from it, so the run never stops on a bad value, and the
other checks treat that value as missing.
"""

import pytest

from datacontract.data_contract import DataContract
from datacontract.engines.ibis.csv_values import strptime_format
from datacontract.model.run import ResultEnum

HEADER = "order_id|quantity|amount|order_date|paid|code"
GOOD_ROWS = [
    "A1|3|19.99|01/02/2026|true|007",
    "A2|2|5.00|15/02/2026|false|010",
    "A3|1|7.50|28/02/2026|true|100",
]


def _contract(
    path, quantity_options="", order_date_options="\n        logicalTypeOptions:\n          format: dd/MM/yyyy"
):
    return f"""apiVersion: v3.2.0
kind: DataContract
id: orders
name: orders
version: 1.0.0
status: active
servers:
  - server: local
    type: local
    format: csv
    path: {path}
schema:
  - name: orders
    quality:
      - type: sql
        query: SELECT COUNT(*) FROM orders WHERE code = '007'
        mustBe: 1
    properties:
      - name: order_id
        logicalType: string
        primaryKey: true
      - name: quantity
        logicalType: integer{quantity_options}
      - name: amount
        logicalType: number
      - name: order_date
        logicalType: date{order_date_options}
      - name: paid
        logicalType: boolean
      - name: code
        logicalType: string
"""


def _test(tmp_path, rows, include_failed_samples=False, **options):
    data = tmp_path / "orders.csv"
    data.write_text("\n".join([HEADER, *rows]) + "\n")
    contract = _contract(data, **options)
    return DataContract(
        data_contract_str=contract, inline_references=False, include_failed_samples=include_failed_samples
    ).test()


def _type_check(run, field):
    return next(c for c in run.checks if c.type == "field_type" and c.field == field)


def _with(column, value, row=1):
    """The good rows with one cell replaced."""
    rows = [r.split("|") for r in GOOD_ROWS]
    rows[row][HEADER.split("|").index(column)] = value
    return ["|".join(r) for r in rows]


def test_a_valid_file_passes_a_type_check_per_typed_column(tmp_path):
    run = _test(tmp_path, GOOD_ROWS)
    print(run.pretty())
    assert run.result == ResultEnum.passed
    assert {c.field for c in run.checks if c.type == "field_type"} == {"quantity", "amount", "order_date", "paid"}


@pytest.mark.parametrize(
    "column, value",
    [
        ("quantity", "two"),
        ("quantity", "2.50"),
        ("quantity", "2.00"),
        ("amount", "5,00"),
        ("order_date", "31/02/2026"),
        ("order_date", "2026-02-15"),
        ("paid", "ja"),
    ],
)
def test_a_value_of_the_wrong_type_fails_only_the_type_check_of_its_column(tmp_path, column, value):
    run = _test(tmp_path, _with(column, value))
    print(run.pretty())
    assert run.result == ResultEnum.failed
    failed = [c for c in run.checks if c.result != ResultEnum.passed]
    assert [(c.type, c.field) for c in failed] == [("field_type", column)]
    assert failed[0].reason == f"Actual invalid_count({column}) was 1, expected = 0"


def test_every_bad_value_is_counted(tmp_path):
    rows = _with("quantity", "two")
    rows[2] = rows[2].replace("|1|", "|1.5|")
    run = _test(tmp_path, rows)
    assert _type_check(run, "quantity").reason == "Actual invalid_count(quantity) was 2, expected = 0"


def test_an_empty_value_is_missing_not_of_the_wrong_type(tmp_path):
    run = _test(tmp_path, _with("quantity", ""))
    print(run.pretty())
    assert _type_check(run, "quantity").result == ResultEnum.passed


def test_a_bad_value_is_missing_for_the_other_checks_on_its_column(tmp_path):
    # A cast would round 3.50 to 4, which fails the maximum of 3; as a missing value, only the type check fails
    run = _test(
        tmp_path,
        _with("quantity", "3.50", row=2),
        quantity_options="\n        logicalTypeOptions:\n          maximum: 3",
    )
    print(run.pretty())
    failed = [(c.type, c.field) for c in run.checks if c.result != ResultEnum.passed]
    assert failed == [("field_type", "quantity")]


def test_a_bad_value_in_a_required_column_is_also_missing(tmp_path):
    run = _test(tmp_path, _with("quantity", "two"), quantity_options="\n        required: true")
    print(run.pretty())
    failed = [(c.type, c.field) for c in run.checks if c.result != ResultEnum.passed]
    assert failed == [("field_type", "quantity"), ("field_required", "quantity")]


def test_the_failed_samples_show_the_bad_value(tmp_path):
    run = _test(tmp_path, _with("quantity", "two"), include_failed_samples=True)
    assert _type_check(run, "quantity").failedSamples == [{"order_id": "A2", "quantity": "two"}]


def test_the_diagnostics_name_the_type_and_format(tmp_path):
    run = _test(tmp_path, _with("order_date", "2026-02-15"))
    assert _type_check(run, "order_date").diagnostics["constraint"] == {"type": "DATE", "format": "dd/MM/yyyy"}


def test_a_text_column_keeps_its_value(tmp_path):
    # The quality rule counts code '007', which a column typed by inference would read as 7
    run = _test(tmp_path, GOOD_ROWS)
    assert next(c for c in run.checks if c.type == "model_quality_sql").result == ResultEnum.passed


def test_a_date_without_a_format_is_iso_8601(tmp_path):
    rows = [_with("order_date", "2026-02-0" + str(i + 1), row=i)[i] for i in range(len(GOOD_ROWS))]
    run = _test(tmp_path, rows, order_date_options="")
    print(run.pretty())
    assert _type_check(run, "order_date").result == ResultEnum.passed


def test_a_date_in_another_format_without_a_declared_format_fails(tmp_path):
    run = _test(tmp_path, GOOD_ROWS, order_date_options="")
    assert _type_check(run, "order_date").result == ResultEnum.failed


def test_a_format_that_cannot_be_checked_is_a_warning(tmp_path):
    options = "\n        logicalTypeOptions:\n          format: yyyy-QQQ"
    run = _test(tmp_path, GOOD_ROWS, order_date_options=options)
    check = _type_check(run, "order_date")
    assert check.result == ResultEnum.warning
    assert check.reason == "The format 'yyyy-QQQ' cannot be checked; values are read as ISO 8601."


@pytest.mark.parametrize(
    "pattern, expected",
    [
        ("dd/MM/yyyy", "%d/%m/%Y"),
        ("yyyy-MM-dd'T'HH:mm:ss.SSSxxx", "%Y-%m-%dT%H:%M:%S.%g%z"),
        ("yyyy-MM-dd'T'HH:mm:ssXXX", None),
        ("d MMM yyyy", "%-d %b %Y"),
        ("hh:mm a", "%I:%M %p"),
        ("''yy", "'%y"),
        ("yyyy-QQQ", None),
        ("'unterminated", None),
    ],
)
def test_a_java_date_pattern_as_strptime(pattern, expected):
    assert strptime_format(pattern) == expected
