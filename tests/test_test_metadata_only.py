import xml.etree.ElementTree as ET

from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract
from datacontract.output.junit_test_results import write_junit_test_results

runner = CliRunner()

SKIP_REASON = "Row-value check disabled by --metadata-only"

# Value-level constraints that the fixture data violates (duplicate order_id,
# an email without an @, a negative amount), so without --metadata-only the
# value checks demonstrably execute and fail.
CSV_CONTRACT = """
apiVersion: v3.0.2
kind: DataContract
id: metadata_only_csv_test
version: 1.0.0
status: active
servers:
  - server: local
    type: local
    path: ./fixtures/diagnostics/data/orders.csv
    format: csv
schema:
  - name: orders
    properties:
      - name: order_id
        logicalType: integer
        required: true
        unique: true
      - name: email
        logicalType: string
        required: true
        logicalTypeOptions:
          pattern: "^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+$"
      - name: amount
        logicalType: integer
        logicalTypeOptions:
          minimum: 0
"""

VALUE_CHECK_TYPES = {"field_required", "field_unique", "field_regex", "field_minimum"}

# Parquet carries real types, so field_type checks are generated (CSV skips them).
PARQUET_CONTRACT = """
apiVersion: v3.0.2
kind: DataContract
id: metadata_only_parquet_test
version: 1.0.0
status: active
servers:
  - server: local
    type: local
    path: ./fixtures/parquet/data/combined.parquet
    format: parquet
schema:
  - name: combined
    properties:
      - name: integer_field
        logicalType: integer
        required: true
        unique: true
      - name: string_field
        logicalType: string
"""


def test_without_flag_value_checks_execute():
    run = DataContract(data_contract_str=CSV_CONTRACT).test()
    print(run.pretty())
    assert run.result == "failed"
    results_by_type = {check.type: check.result for check in run.checks}
    assert results_by_type["field_unique"] == "failed"
    assert results_by_type["field_regex"] == "failed"
    assert results_by_type["field_minimum"] == "failed"
    assert not any(check.result == "skipped" for check in run.checks)


def test_metadata_only_skips_value_checks():
    run = DataContract(data_contract_str=CSV_CONTRACT, metadata_only=True).test()
    print(run.pretty())
    assert run.result == "passed"
    # order_id and email are both required, so field_required appears twice.
    value_checks = [check for check in run.checks if check.type in VALUE_CHECK_TYPES]
    assert len(value_checks) == 5
    for check in value_checks:
        assert check.result == "skipped"
        assert check.reason == SKIP_REASON
    present_checks = [check for check in run.checks if check.type == "field_is_present"]
    assert len(present_checks) == 3
    assert all(check.result == "passed" for check in present_checks)


def test_metadata_only_passes_when_introspection_checks_pass():
    run = DataContract(data_contract_str=PARQUET_CONTRACT, metadata_only=True).test()
    print(run.pretty())
    assert run.result == "passed"
    type_checks = [check for check in run.checks if check.type == "field_type"]
    assert len(type_checks) == 2
    assert all(check.result == "passed" for check in type_checks)
    skipped_checks = [check for check in run.checks if check.result == "skipped"]
    assert {check.type for check in skipped_checks} == {"field_required", "field_unique"}


def test_metadata_only_junit_output(tmp_path):
    run = DataContract(data_contract_str=CSV_CONTRACT, metadata_only=True).test()
    output_path = tmp_path / "TEST-datacontract.xml"
    write_junit_test_results(run, output_path)
    testsuite = ET.parse(output_path).getroot()
    assert int(testsuite.get("skipped")) == 5
    skipped_messages = [
        skipped.get("message") for testcase in testsuite.iter("testcase") for skipped in testcase.iter("skipped")
    ]
    assert len(skipped_messages) == 5
    assert all(message == SKIP_REASON for message in skipped_messages)


def test_metadata_only_cli_option(tmp_path):
    contract_path = tmp_path / "datacontract.yaml"
    contract_path.write_text(CSV_CONTRACT)
    result = runner.invoke(
        app,
        ["test", "--checks", "schema", "--metadata-only", str(contract_path)],
    )
    assert result.exit_code == 0
    assert "skipped" in result.stdout
    assert "(5 skipped)" in result.stdout


# Every check here reads row values (rowCount, custom SQL, freshness, retention),
# so under --metadata-only only the field presence check executes.
SLA_AND_SQL_CONTRACT = """
apiVersion: v3.0.2
kind: DataContract
id: metadata_only_sla_sql_test
version: 1.0.0
status: active
servers:
  - server: local
    type: local
    path: ./fixtures/diagnostics/data/orders.csv
    format: csv
schema:
  - name: orders
    quality:
      - type: library
        metric: rowCount
        mustBeGreaterThan: 1
      - type: sql
        description: amounts are positive
        query: SELECT MIN(amount) FROM orders
        mustBeGreaterThan: 0
    properties:
      - name: order_id
        logicalType: integer
slaProperties:
  - property: freshness
    value: 24
    unit: h
    element: orders.order_id
  - property: retention
    value: 1
    unit: y
    element: orders.order_id
"""


def test_metadata_only_skips_servicelevel_and_custom_sql():
    run = DataContract(data_contract_str=SLA_AND_SQL_CONTRACT, metadata_only=True).test()
    print(run.pretty())
    assert run.result == "passed"
    skipped = {check.type: check.reason for check in run.checks if check.result == "skipped"}
    assert set(skipped) == {
        "row_count",
        "model_quality_sql",
        "servicelevel_freshness",
        "servicelevel_retention",
    }
    assert all(reason == SKIP_REASON for reason in skipped.values())


def test_metadata_only_all_skipped_remains_unknown():
    run = DataContract(
        data_contract_str=SLA_AND_SQL_CONTRACT,
        check_categories={"quality"},
        metadata_only=True,
    ).test()
    print(run.pretty())
    assert run.result == "unknown"
    assert {check.type for check in run.checks} == {"row_count", "model_quality_sql"}
    assert all(check.result == "skipped" and check.reason == SKIP_REASON for check in run.checks)


def test_metadata_only_keeps_json_record_validation(tmp_path):
    json_path = tmp_path / "orders.json"
    json_path.write_text('[{"email": "not-an-email"}]')
    contract = f"""
apiVersion: v3.0.2
kind: DataContract
id: metadata_only_json_test
version: 1.0.0
status: active
servers:
  - server: local
    type: local
    path: "{json_path}"
    format: json
    delimiter: array
schema:
  - name: orders
    properties:
      - name: email
        logicalType: string
        logicalTypeOptions:
          pattern: "^[^@]+@[^@]+$"
"""

    run = DataContract(data_contract_str=contract, metadata_only=True).test()
    print(run.pretty())
    assert run.result == "failed"
    assert any(check.engine == "jsonschema" and check.result == "failed" for check in run.checks)


def test_metadata_only_ci_cli_option(tmp_path):
    contract_path = tmp_path / "datacontract.yaml"
    contract_path.write_text(CSV_CONTRACT)
    result = runner.invoke(app, ["ci", str(contract_path), "--metadata-only"])
    assert result.exit_code == 0
    assert "skipped" in result.stdout
