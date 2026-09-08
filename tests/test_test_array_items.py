"""The array constraints run against real data.

Three rows: one satisfies every constraint, one is too short, one repeats an
element. Each check has to find exactly the row that breaks its own rule.
"""

from datacontract.data_contract import DataContract

DATA = "fixtures/array-items/data/tags.json"


def contract(options: str) -> str:
    return f"""
apiVersion: v3.0.2
kind: DataContract
id: array_items
version: 1.0.0
status: active
servers:
  - server: local
    type: local
    path: {DATA}
    format: json
    delimiter: array
schema:
  - name: tags
    properties:
      - name: id
        logicalType: string
      - name: tags
        logicalType: array
        logicalTypeOptions:
{options}
        items:
          logicalType: string
"""


def check_named(run, fragment: str):
    return next(c for c in run.checks if fragment in c.name)


def test_min_items_finds_the_short_array():
    run = DataContract(data_contract_str=contract("          minItems: 2")).test()

    check = check_named(run, "at least 2 items")
    assert check.result == "failed"
    assert "was 1" in check.reason


def test_min_items_passes_when_every_array_is_long_enough():
    run = DataContract(data_contract_str=contract("          minItems: 1")).test()

    assert check_named(run, "at least 1 items").result == "passed"


def test_max_items_finds_the_long_array():
    run = DataContract(data_contract_str=contract("          maxItems: 2")).test()

    check = check_named(run, "at most 2 items")
    assert check.result == "failed"
    assert "was 1" in check.reason


def test_unique_items_finds_the_repeated_element():
    run = DataContract(data_contract_str=contract("          uniqueItems: true")).test()

    check = check_named(run, "no duplicate items")
    assert check.result == "failed"
    assert "was 1" in check.reason


def test_a_contract_that_holds_passes():
    run = DataContract(data_contract_str=contract("          minItems: 1\n          maxItems: 3")).test()

    assert run.result == "passed"


def test_a_column_that_is_not_an_array_reports_an_error(tmp_path):
    """A silently passing check would be worse than one that says it could not run."""
    csv = tmp_path / "drift.csv"
    csv.write_text('id,tags\na,"x,y"\n')
    run = DataContract(
        data_contract_str=f"""
apiVersion: v3.0.2
kind: DataContract
id: drift
version: 1.0.0
status: active
servers:
  - server: local
    type: local
    path: {csv}
    format: csv
schema:
  - name: drift
    properties:
      - name: tags
        logicalType: array
        logicalTypeOptions:
          minItems: 2
        items:
          logicalType: string
"""
    ).test()

    check = check_named(run, "at least 2 items")
    assert check.result == "error"
    assert "not an array" in check.reason
