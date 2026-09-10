"""Array hops in a check's field path, and the predicates they compile to."""

import ibis
import pytest

from datacontract.engines.ibis.ibis_check_execute import _missing_expr, _resolve_dtype, _row_predicate

TABLE = ibis.table(
    {
        "order_id": "string",
        "customer": "struct<name:string,tags:array<struct<tag_id:string>>>",
        "items": "array<struct<sku:string,parts:array<struct<part_no:string>>>>",
    },
    name="orders",
)
COLUMNS = {c.lower(): c for c in TABLE.columns}


@pytest.mark.parametrize(
    "path,expected",
    [
        ("order_id", "string"),
        ("customer.name", "string"),
        ("items[].sku", "string"),
        ("customer.tags[].tag_id", "string"),
        ("items[].parts[].part_no", "string"),
    ],
)
def test_resolve_dtype_steps_through_array_elements(path, expected):
    assert str(_resolve_dtype(TABLE.schema(), path)) == expected


def test_resolve_dtype_is_case_insensitive_across_an_array_hop():
    assert str(_resolve_dtype(TABLE.schema(), "ITEMS[].SKU")) == "string"


def _sql(path):
    predicate = _row_predicate(TABLE, COLUMNS, path, lambda c: _missing_expr(c, None))
    return " ".join(str(ibis.to_sql(TABLE.filter(predicate).count(), dialect="databricks")).split())


def test_a_plain_path_compiles_to_a_column_predicate():
    assert "FILTER(" not in _sql("customer.name")


def test_an_array_hop_compiles_to_a_predicate_over_the_elements():
    # A predicate over the array keeps one row per parent, so counts stay in
    # parent rows and an empty array is never a violation.
    sql = _sql("items[].sku")
    assert "SIZE(FILTER(`t0`.`items`" in sql
    assert "`sku`)ISNULL" in sql.replace(" ", "")


def test_nested_array_hops_compile_to_nested_predicates():
    assert _sql("items[].parts[].part_no").count("FILTER(") == 2


UPPERCASE = ibis.table(
    {"ORDER_ID": "string", "CUSTOMER": "struct<NAME:string>", "ITEMS": "array<struct<SKU:string>>"},
    name="ORDERS",
)
UPPERCASE_COLUMNS = {c.lower(): c for c in UPPERCASE.columns}


@pytest.mark.parametrize("path", ["customer.name", "items[].sku"])
def test_a_path_resolves_to_a_value_when_the_backend_reports_uppercase_names(path):
    # _resolve_dtype already folds case; the value side has to agree, or presence
    # and type checks pass while the count checks raise KeyError.
    predicate = _row_predicate(UPPERCASE, UPPERCASE_COLUMNS, path, lambda c: _missing_expr(c, None))
    assert "IS NULL" in str(ibis.to_sql(UPPERCASE.filter(predicate).count(), dialect="databricks"))


def test_item_duplicate_samples_use_the_same_predicate_as_the_check():
    # `unique` on an array item is not a column lookup, so the sample path has to
    # take the array branch too or it silently reports no samples.
    import pandas as pd

    from datacontract.engines.checks.check_spec import CheckSpec, MetricType
    from datacontract.engines.ibis.ibis_check_execute import _samples_for

    t = ibis.memtable(
        pd.DataFrame(
            {
                "order_id": ["clean", "repeats"],
                "items": [[{"sku": "A"}, {"sku": "B"}], [{"sku": "C"}, {"sku": "C"}]],
            }
        )
    )
    spec = CheckSpec(
        key="orders__items[].sku__field_unique",
        category="schema",
        type="field_unique",
        name="unique",
        model="orders",
        field="items[].sku",
        metric=MetricType.DUPLICATE_COUNT,
        columns=["items[].sku"],
    )
    samples = _samples_for(t, {c.lower(): c for c in t.columns}, t.schema(), spec, ["order_id"], set())

    assert samples is not None
    assert [row["order_id"] for row in samples] == ["repeats"]
