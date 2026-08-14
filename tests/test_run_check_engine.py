from datacontract.data_contract import DataContract

ALLOWED_ENGINES = {"datacontract", "ibis", "ibis-metadata-only", "jsonschema", "dbt"}

CONTRACT = """
apiVersion: v3.0.2
kind: DataContract
id: engine_test
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


def test_full_run_reports_one_engine_throughout():
    run = DataContract(data_contract_str=CONTRACT).test()
    assert {check.engine for check in run.checks} == {"ibis"}


def test_metadata_only_run_reports_one_engine_throughout():
    # The ibis-metadata-only engine is set for the whole run - the skipped row-value checks
    # carry it too.
    run = DataContract(data_contract_str=CONTRACT, metadata_only=True).test()
    assert {check.engine for check in run.checks} == {"ibis-metadata-only"}
    assert any(check.result == "skipped" for check in run.checks)


def test_engines_stay_within_the_documented_set():
    run = DataContract(data_contract_str=CONTRACT).test()
    assert {check.engine for check in run.checks} <= ALLOWED_ENGINES


def test_missing_file_is_reported_by_the_cli_itself():
    run = DataContract(data_contract_file="does-not-exist.yaml").test()
    assert [check.engine for check in run.checks] == ["datacontract"]
