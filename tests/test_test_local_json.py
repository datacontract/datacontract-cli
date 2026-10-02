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
