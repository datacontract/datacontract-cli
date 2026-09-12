"""A uniqueness check is a whole-table question; --filter must not narrow it.

Reproduces the bug at production scale: a windowed `field_unique` passed for
45 days on a table that, read unfiltered, reported 8 duplicate primary keys.
`tests/fixtures/row-filter-duplicate/data.csv` is the same shape in miniature
-- id=2 repeats once in batch 1 and once in batch 2, so a filter narrow enough
to see only one of the two hides the duplicate.
"""

from datacontract.data_contract import DataContract

CONTRACT = "fixtures/row-filter-duplicate/datacontract.yaml"


def _unique_check(run):
    return next(c for c in run.checks if c.type == "field_unique")


def test_unfiltered_duplicate_is_caught():
    run = DataContract(data_contract_file=CONTRACT).test()
    print(run.pretty())
    check = _unique_check(run)
    assert check.result == "failed"


def test_a_filter_that_hides_half_the_duplicate_does_not_hide_the_check():
    """Before this fix: filtering to batch = 1 leaves id 1 and 2 -- each
    appearing once -- so the old, filtered duplicate query reported no
    duplicate and the check passed. It must still fail."""
    run = DataContract(data_contract_file=CONTRACT, filter="batch = 1").test()
    print(run.pretty())
    assert run.filters == {"data": "batch = 1"}
    check = _unique_check(run)
    assert check.result == "failed"


def test_other_checks_still_see_the_filtered_table():
    """The fix is scoped to DUPLICATE_COUNT; row_count must still narrow --
    otherwise this would look like the filter stopped applying at all."""
    run = DataContract(data_contract_file=CONTRACT, filter="batch = 1").test()
    print(run.pretty())
    row_count_check = next(c for c in run.checks if c.type == "row_count")
    assert row_count_check.result == "passed"  # mustBe: 2, and only 2 rows match batch = 1


def test_a_filter_that_would_not_even_compile_does_not_block_the_duplicate_check():
    """DUPLICATE_COUNT does not read the filtered table, so it does not need
    the filter to compile either -- unlike every check that does read it."""
    run = DataContract(data_contract_file=CONTRACT, filter="no_such_column = 1").test()
    print(run.pretty())
    check = _unique_check(run)
    assert check.result == "failed"
    assert check.reason is None or "Could not apply row filter" not in check.reason
