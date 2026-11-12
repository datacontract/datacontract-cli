"""A property name is one whole name: `datacontract test` never splits it at a dot or cuts it at a bracket.

Nesting comes only from the declared structure (`properties`, `items`, `map`).
"""

import duckdb
import pytest

from datacontract.data_contract import DataContract
from datacontract.model.run import ResultEnum

CONTRACT = """apiVersion: v3.1.0
kind: DataContract
id: rates
version: 1.0.0
status: active
servers:
  - server: production
    type: duckdb
    database: {database}
schema:
  - name: t
    physicalType: table
    properties:
{properties}
"""

FLAT_PROPERTIES = """      - name: Amount [A]
        logicalType: number
        required: true
        unique: true
        logicalTypeOptions:
          minimum: 0
        quality:
          - type: sql
            query: SELECT COUNT(*) FROM t WHERE {property} < 0
            mustBe: 0
      - name: Rate.x
        logicalType: number
        required: true
        unique: true
        logicalTypeOptions:
          minimum: 0
        quality:
          - type: sql
            query: SELECT COUNT(*) FROM t WHERE {property} < 0
            mustBe: 0
      - name: plain
        logicalType: number"""


def _test(tmp_path, ddl, rows, properties):
    database = tmp_path / "t.duckdb"
    con = duckdb.connect(str(database))
    con.sql(ddl)
    con.sql(f"INSERT INTO t VALUES {rows}")
    con.close()
    return DataContract(data_contract_str=CONTRACT.format(database=database, properties=properties)).test()


def _flat(tmp_path, rows):
    return _test(tmp_path, 'CREATE TABLE t ("Amount [A]" DOUBLE, "Rate.x" DOUBLE, plain DOUBLE)', rows, FLAT_PROPERTIES)


def _results(run):
    return {(check.field, check.type): check.result for check in run.checks}


def test_columns_named_with_a_dot_or_a_bracket_are_found_and_checked(tmp_path):
    run = _flat(tmp_path, "(1, 2, 3), (4, 5, 6)")

    assert run.result == ResultEnum.passed, [check.reason for check in run.checks if check.reason]
    results = _results(run)
    for field in ("Amount [A]", "Rate.x"):
        for check_type in ("field_is_present", "field_type", "field_required", "field_unique", "field_minimum"):
            assert results[(field, check_type)] == ResultEnum.passed, (field, check_type)


@pytest.mark.parametrize("field", ["Amount [A]", "Rate.x"])
def test_rules_on_a_column_named_with_a_dot_or_a_bracket_fail_on_the_rows_that_violate_them(tmp_path, field):
    # one row repeats the value of the other, one is missing, one is negative
    rows = "(1, 1, 3), (1, 1, 3), (NULL, NULL, 3), (-5, -5, 3)"
    run = _flat(tmp_path, rows)

    results = _results(run)
    assert results[(field, "field_type")] == ResultEnum.passed
    assert results[(field, "field_required")] == ResultEnum.failed
    assert results[(field, "field_unique")] == ResultEnum.failed
    assert results[(field, "field_minimum")] == ResultEnum.failed
    assert not [check for check in run.checks if "not found" in (check.reason or "")]


def test_the_property_placeholder_of_a_sql_rule_names_a_column_with_a_dot(tmp_path):
    properties = """      - name: Rate.x
        logicalType: number
        quality:
          - type: sql
            query: SELECT COUNT(*) FROM t WHERE {property} < 0
            mustBe: 1"""
    run = _test(tmp_path, 'CREATE TABLE t ("Rate.x" DOUBLE)', "(1), (-1), (2)", properties)

    quality = next(check for check in run.checks if check.type == "field_quality_sql")
    assert quality.result == ResultEnum.passed, quality.reason


def test_a_field_with_a_dot_inside_a_struct_is_found_and_checked(tmp_path):
    properties = """      - name: s
        logicalType: object
        properties:
          - name: x.y
            logicalType: string
            required: true
            quality:
              - type: sql
                query: SELECT COUNT(*) FROM t WHERE {property} IS NULL
                mustBe: 1"""
    run = _test(tmp_path, 'CREATE TABLE t (s STRUCT("x.y" VARCHAR))', "({'x.y': 'a'}), ({'x.y': NULL})", properties)

    results = _results(run)
    assert results[("s.x.y", "field_is_present")] == ResultEnum.passed
    assert results[("s.x.y", "field_type")] == ResultEnum.passed
    assert results[("s.x.y", "field_required")] == ResultEnum.failed
    assert results[("s.x.y", "field_quality_sql")] == ResultEnum.passed


STRUCT_PROPERTIES = """      - name: customer.name
        logicalType: string
        required: true"""


def _presence(run):
    return next(c for c in run.checks if (c.field, c.type) == ("customer.name", "field_is_present"))


def test_a_name_written_like_a_struct_path_is_a_missing_column_and_the_reason_points_to_the_struct(tmp_path):
    run = _test(tmp_path, "CREATE TABLE t (customer STRUCT(name VARCHAR))", "({'name': 'a'})", STRUCT_PROPERTIES)

    presence = _presence(run)
    assert presence.result == ResultEnum.failed
    assert "'customer' has a field 'name'" in presence.reason
    assert "declare it under the properties of 'customer'" in presence.reason


def test_a_missing_column_with_a_dot_in_its_name_has_no_hint_without_a_matching_struct_field(tmp_path):
    run = _test(tmp_path, "CREATE TABLE t (customer VARCHAR)", "('a')", STRUCT_PROPERTIES)

    presence = _presence(run)
    assert presence.result == ResultEnum.failed
    assert presence.reason == "Required column 'customer.name' is missing"
