"""Unit tests for the SQL Server (mssql) pattern-check fallback.

SQL Server has no native regex operator, so the ibis mssql backend cannot
compile ``re_search`` and raises "Compilation rule for RegexSearch operation is
not defined". For pattern checks we fall back to a PATINDEX-based LIKE match,
matching the former soda-core behaviour. See issue #1284.
"""

import ibis
import pytest

from datacontract.engines.ibis.ibis_check_execute import (
    _mssql_like_pattern,
    _mssql_pattern_search,
)


def test_like_compatible_pattern_passes_through():
    pattern = "[0-9][0-9][0-9][0-9][0-9]"
    assert _mssql_like_pattern(pattern) == pattern


def test_like_compatible_pattern_with_literals_and_classes():
    pattern = "[A-Z][A-Z]-[0-9][0-9][0-9]-[A-Z][A-Z]"
    assert _mssql_like_pattern(pattern) == pattern


@pytest.mark.parametrize(
    "pattern",
    [
        "^[0-9]{5}$",  # anchors + quantifier
        ".+@.+",  # wildcard + quantifier
        "[0-9]+",  # quantifier
        r"\d\d\d",  # escape
        "(a|b)",  # group + alternation
    ],
)
def test_real_regex_patterns_are_rejected(pattern):
    with pytest.raises(ValueError, match="SQL Server does not support general regular expressions"):
        _mssql_like_pattern(pattern)


def test_pattern_search_compiles_to_patindex_for_mssql():
    t = ibis.table({"postal_code": "string"}, name="USER")
    predicate = _mssql_pattern_search(t.postal_code, "[0-9][0-9][0-9][0-9][0-9]")
    sql = ibis.to_sql(t.filter(predicate).count(), dialect="mssql")
    assert "PATINDEX('[0-9][0-9][0-9][0-9][0-9]'" in sql
    assert "REGEXP" not in sql.upper()
