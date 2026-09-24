"""A refused `quality.type: sql` query says why it was refused.

A placeholder substituted into the query, such as a field name with a space, can
turn it into SQL that does not parse, and the reason is the only place the user
sees the query as it was run.
"""

import pytest
from open_data_contract_standard.model import (
    DataQuality,
    OpenDataContractStandard,
    SchemaObject,
    SchemaProperty,
    Server,
)

from datacontract.engines.checks.create_checks import create_checks
from datacontract.engines.checks.sql_guard import read_only_query_problem


@pytest.mark.parametrize(
    "query, problem",
    [
        (
            "SELECT count(*) FROM orders WHERE A B IS NULL",
            "it could not be parsed: Invalid expression / Unexpected token at line 1, column 37 (near 'B')",
        ),
        ("SELECT count(*) FROM orders; DROP TABLE orders", "it holds 2 statements"),
        ("DROP TABLE orders", "it is not a read-only query (DROP)"),
        ("ATTACH '/tmp/pwn.db' AS pwn", "it is not a read-only query (ATTACH)"),
        ("", "it is empty"),
    ],
)
def test_a_refused_query_says_why(query, problem):
    assert read_only_query_problem(query, "duckdb") == problem


def test_a_read_only_query_has_no_problem():
    assert read_only_query_problem("SELECT count(*) FROM orders;", "duckdb") is None


def test_the_reason_shows_the_parse_error_and_the_substituted_query():
    quality = DataQuality(type="sql", query="SELECT COUNT(*) FROM {model} WHERE {field} IS NULL", mustBe=0)
    prop = SchemaProperty(name="A B", logicalType="string", quality=[quality])
    schema = SchemaObject(name="orders", physicalType="table", properties=[prop])
    contract = OpenDataContractStandard(version="1", kind="DataContract", apiVersion="v3.1.0", id="x", schema=[schema])

    checks = create_checks(contract, Server(server="s", type="local", format="csv"))
    check = next(c for c in checks if c.type == "field_quality_sql")

    assert check.preset_result == "failed"
    assert "(duckdb SQL): it could not be parsed: Invalid expression / Unexpected token" in check.preset_reason
    assert "Query: SELECT COUNT(*) FROM orders WHERE A B IS NULL" in check.preset_reason
