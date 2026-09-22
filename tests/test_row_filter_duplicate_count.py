"""--filter scopes a uniqueness check to the keys the window contains: the
check reads every row whose key occurs in the window -- duplicates within the
window and across its edge, not ones wholly outside it.

tests/fixtures/row-filter-duplicate/data.csv, by batch:
  1: ids 1, 2      2: ids 3, 2       -> id 2 repeats across batches 1 and 2
  3: ids 5, 5                        -> repeats within batch 3
  4: id 6                            -> no duplicate of its own
  5: ids NULL, NULL                  -> NULL keys, never duplicates of each other
"""

from datacontract.data_contract import DataContract

CONTRACT = "fixtures/row-filter-duplicate/datacontract.yaml"


def _unique_check(run):
    return next(c for c in run.checks if c.type == "field_unique")


def test_a_duplicate_across_the_window_edge_is_caught():
    """Batch 1 holds id 2 once; its other occurrence is in batch 2. Reading only
    the filtered rows found no duplicate here and passed."""
    run = DataContract(data_contract_file=CONTRACT, filter="batch = 1").test()
    print(run.pretty())
    assert run.filters == {"data": "batch = 1"}
    assert _unique_check(run).result == "failed"


def test_a_duplicate_within_the_window_is_caught():
    run = DataContract(data_contract_file=CONTRACT, filter="batch = 3").test()
    print(run.pretty())
    assert _unique_check(run).result == "failed"


def test_a_duplicate_wholly_outside_the_window_is_not_its_to_report():
    """Batch 4's only key is 6, which never repeats. Ids 2 and 5 do, but
    none of them occurs in batch 4 -- they are other windows' duplicates."""
    run = DataContract(data_contract_file=CONTRACT, filter="batch = 4").test()
    print(run.pretty())
    assert _unique_check(run).result == "passed"


def test_null_keys_are_not_duplicates():
    """Two NULL ids are not a duplicate, as with SQL UNIQUE -- filtered or not."""
    run = DataContract(data_contract_file=CONTRACT, filter="batch = 5").test()
    print(run.pretty())
    assert _unique_check(run).result == "passed"
    run = DataContract(data_contract_file=CONTRACT).test()
    print(run.pretty())
    assert _unique_check(run).diagnostics["value"] == 2  # ids 2 and 5, not the NULL pair


def test_a_filter_that_does_not_compile_errors_the_duplicate_check_too():
    """The check needs the window's keys to know which rows to read, so a
    predicate that cannot be applied errors it like every other row read."""
    run = DataContract(data_contract_file=CONTRACT, filter="no_such_column = 1").test()
    print(run.pretty())
    check = _unique_check(run)
    assert check.result == "error"
    assert "Could not apply row filter" in (check.reason or "")
