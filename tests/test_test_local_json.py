import pytest
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract

runner = CliRunner()


@pytest.mark.skip(reason="https://github.com/sodadata/soda-core/issues/1992")
def _test_cli():
    result = runner.invoke(app, ["test", "./fixtures/local-json/datacontract.yaml"])
    assert result.exit_code == 0


@pytest.mark.skip(reason="https://github.com/sodadata/soda-core/issues/1992")
def _test_local_json():
    data_contract = DataContract(data_contract_file="fixtures/local-json/datacontract.yaml")
    run = data_contract.test()
    print(run)
    assert run.result == "passed"


def json_contract(path, properties: str) -> str:
    return f"""
apiVersion: v3.2.0
kind: DataContract
id: orders
version: 1.0.0
status: active
servers:
  - server: local
    type: local
    path: {path}
    format: json
    delimiter: array
schema:
  - name: orders
    properties:
{properties}
"""


ORDER_PROPERTIES = """      - name: id
        logicalType: string
        required: true
      - name: qty
        logicalType: integer
        logicalTypeOptions:
          minimum: 1
      - name: status
        logicalType: string
        required: true"""


def test_a_record_that_breaks_the_json_schema_does_not_stop_the_other_checks(tmp_path):
    # the second record has a qty below the minimum and no status, both also JSON Schema violations
    (tmp_path / "orders.json").write_text('[{"id": "1", "qty": 3, "status": "new"}, {"id": "2", "qty": 0}]')

    run = DataContract(data_contract_str=json_contract(tmp_path / "orders.json", ORDER_PROPERTIES)).test()

    results = {c.name: c.result for c in run.checks}
    assert results["Check that JSON has valid schema"] == "failed"
    assert results["Check that field qty has a minimum of 1"] == "failed"
    assert results["Check that field status has no missing values"] == "failed"
    assert results["Check that field id has no missing values"] == "passed"
    assert None not in results.values()


def test_every_record_that_breaks_the_json_schema_is_reported(tmp_path):
    (tmp_path / "a.json").write_text('[{"id": "1", "status": "new"}, {"id": "2"}]')
    (tmp_path / "b.json").write_text('[{"id": "3"}]')

    run = DataContract(data_contract_str=json_contract(tmp_path / "*.json", ORDER_PROPERTIES)).test()

    schema_checks = [c for c in run.checks if c.name == "Check that JSON has valid schema"]
    assert [c.result for c in schema_checks] == ["failed", "failed"]


def test_json_files_that_do_not_exist_are_reported(tmp_path):
    run = DataContract(data_contract_str=json_contract(tmp_path / "missing.json", ORDER_PROPERTIES)).test()

    check = next(c for c in run.checks if c.name == "Check that JSON has valid schema")
    assert check.result == "warning"
    assert "No files found" in check.reason


def test_a_value_of_the_wrong_type_fails_the_json_schema_check_only(tmp_path):
    (tmp_path / "orders.json").write_text(
        '[{"id": "1", "qty": 3, "status": "new"}, {"id": "2", "qty": "many", "status": "new"}, {"id": "3", "qty": 0, "status": "new"}]'
    )

    run = DataContract(data_contract_str=json_contract(tmp_path / "orders.json", ORDER_PROPERTIES)).test()

    results = {c.name: (c.result, c.reason) for c in run.checks}
    assert results["Check that JSON has valid schema"][0] == "failed"
    assert "qty" in results["Check that JSON has valid schema"][1]
    # the other checks on the column still run, and find the record that breaks them
    assert results["Check that field qty has a minimum of 1"] == (
        "failed",
        "Actual invalid_count(qty) was 1, expected = 0",
    )
    assert not [name for name, (result, _) in results.items() if result == "error"]


@pytest.mark.parametrize("name", ["orders.jsonl", "orders.ndjson"])
def test_newline_delimited_json_files_are_validated(tmp_path, name):
    (tmp_path / name).write_text('{"id": "1", "status": "new"}\n{"id": "2"}\n')
    contract = json_contract(tmp_path / name, ORDER_PROPERTIES).replace("delimiter: array", "delimiter: new_line")

    run = DataContract(data_contract_str=contract).test()

    assert [c.result for c in run.checks if c.name == "Check that JSON has valid schema"] == ["failed"]


@pytest.mark.parametrize(
    "content",
    [
        '[{"id": "1", "qty": 1, "status": "new"}, {"id": "2", "qty": 2, "status": "new"}]',
        '{"id": "1", "qty": 1, "status": "new"}\n\n{"id": "2", "qty": 2, "status": "new"}\n',
    ],
    ids=["array", "newline-delimited"],
)
def test_without_a_delimiter_json_files_are_read_as_duckdb_reads_them(tmp_path, content):
    (tmp_path / "orders.json").write_text(content)
    contract = json_contract(tmp_path / "orders.json", ORDER_PROPERTIES).replace("    delimiter: array\n", "")

    run = DataContract(data_contract_str=contract).test()

    assert run.result == "passed", [(c.name, c.reason) for c in run.checks if c.result != "passed"]
