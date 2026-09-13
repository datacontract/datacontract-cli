import os
from unittest.mock import Mock

import pytest
from open_data_contract_standard.model import (
    DataQuality,
    OpenDataContractStandard,
    SchemaObject,
    SchemaProperty,
    Server,
    ServiceLevelAgreementProperty,
)
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract
from datacontract.engines.data_contract_test import execute_data_contract_test
from datacontract.model.run import Check, ResultEnum, Run
from tests.test_hana_schema_check import DataConnection, FakeConnection, catalog_response, column


def test_hana_test_flow_bypasses_soda(monkeypatch):
    from datacontract.engines.hana import check_hana_execute as hana_module

    def fake_check_hana_execute(
        run,
        data_contract,
        server,
        schema_name="all",
        check_categories=None,
        dry_run=False,
        metadata_only=False,
    ):
        run.checks.append(Check(type="model_exists", result=ResultEnum.passed, engine="hana"))

    monkeypatch.setattr(hana_module, "check_hana_execute", fake_check_hana_execute)
    data_contract = OpenDataContractStandard(
        id="hana-test",
        schema=[SchemaObject(name="ORDERS", properties=[SchemaProperty(name="ID", logicalType="integer")])],
        servers=[Server(server="production", type="hana", host="hana.example.com", port=443, schema="SALES")],
    )
    run = Run.create_run()

    execute_data_contract_test(data_contract, run)

    assert [check.engine for check in run.checks] == ["hana"]
    assert run.checks[0].result == ResultEnum.passed


def _mode_contract():
    return OpenDataContractStandard(
        apiVersion="v3.2.0",
        kind="DataContract",
        id="hana-modes",
        name="HANA modes",
        version="1.0.0",
        status="draft",
        servers=[Server(server="production", type="hana", host="hana.example.com", port=443, schema="SALES")],
        schema=[
            SchemaObject(
                name="orders",
                physicalName="ORDERS",
                properties=[
                    SchemaProperty(
                        name="id",
                        physicalName="ID",
                        logicalType="integer",
                        required=True,
                        primaryKey=True,
                        unique=True,
                        logicalTypeOptions={
                            "minimum": 0,
                            "maximum": 100,
                            "exclusiveMinimum": -1,
                            "exclusiveMaximum": 101,
                        },
                    ),
                    SchemaProperty(
                        name="status",
                        physicalName="STATUS",
                        logicalType="string",
                        logicalTypeOptions={
                            "minLength": 1,
                            "maxLength": 10,
                            "pattern": "[A-Z]+",
                        },
                        enum=[{"value": "OPEN"}, {"value": "PAID"}],
                        quality=[
                            DataQuality(metric="nullValues", unit="percent", mustBeLessThan=5),
                            DataQuality(metric="missingValues", mustBe=0),
                            DataQuality(metric="invalidValues", arguments={"validValues": ["OPEN", "PAID"]}, mustBe=0),
                            DataQuality(metric="duplicateValues", mustBe=0),
                            DataQuality(type="sql", query="SELECT COUNT({field}) FROM {model}", mustBe=0),
                        ],
                    ),
                    SchemaProperty(name="updated_at", physicalName="UPDATED_AT", logicalType="timestamp"),
                ],
                quality=[
                    DataQuality(metric="rowCount", mustBeGreaterThan=0),
                    DataQuality(type="sql", query="SELECT COUNT(*) FROM {model}", mustBeGreaterThan=0),
                ],
            )
        ],
        slaProperties=[
            ServiceLevelAgreementProperty(property=prop, element="orders.updated_at", value=24, unit="h")
            for prop in ("freshness", "retention")
        ],
    ).model_dump_json(by_alias=True, exclude_none=True)


def _catalog_connection():
    connection = FakeConnection(
        catalog_response(
            [
                column("ID", "INTEGER"),
                column("STATUS", "NVARCHAR"),
                column("UPDATED_AT", "TIMESTAMP"),
            ]
        )
        + [(lambda sql, params: True, [(0,)])]
    )
    connection.close = Mock()
    return connection


@pytest.mark.parametrize("metadata_only", [False, True])
def test_hana_dry_run_lists_native_checks_without_connecting(monkeypatch, metadata_only):
    contract = _mode_contract()
    connection = _catalog_connection()
    monkeypatch.setattr("datacontract.engines.hana.check_hana_execute.get_connection", lambda server: connection)
    executed = DataContract(data_contract_str=contract, metadata_only=metadata_only).test()

    connect = Mock(side_effect=AssertionError("A dry run must not connect"))
    monkeypatch.setattr("datacontract.engines.hana.check_hana_execute.get_connection", connect)
    planned = DataContract(data_contract_str=contract, dry_run=True, metadata_only=metadata_only).test()

    connect.assert_not_called()
    assert planned.dryRun is True
    assert planned.result == ResultEnum.skipped
    assert planned.checks
    assert sorted(c.key for c in planned.checks) == sorted(c.key for c in executed.checks)
    assert all(c.result == ResultEnum.skipped and c.implementation for c in planned.checks)
    for check in planned.checks:
        expected_reason = (
            "Row-value check disabled by --metadata-only"
            if metadata_only and check.type in _ROW_CHECK_TYPES
            else "Dry run: check not executed"
        )
        assert check.reason == expected_reason


_ROW_CHECK_TYPES = {
    "field_required",
    "field_enum",
    "field_unique",
    "field_min_length",
    "field_max_length",
    "field_minimum",
    "field_maximum",
    "field_not_equal",
    "field_regex",
    "field_null_values",
    "field_missing_values",
    "field_invalid_values",
    "field_duplicate_values",
    "field_quality_sql",
    "model_quality_sql",
    "row_count",
    "servicelevel_freshness",
    "servicelevel_retention",
}


def test_hana_metadata_only_reads_catalog_and_reports_skipped_checks(monkeypatch):
    connection = _catalog_connection()
    original_response = connection.response_for

    def catalog_only(sql, params):
        assert any(catalog in sql for catalog in ("SYS.TABLE_COLUMNS", "SYS.VIEW_COLUMNS"))
        return original_response(sql, params)

    connection.response_for = catalog_only
    monkeypatch.setattr("datacontract.engines.hana.check_hana_execute.get_connection", lambda server: connection)
    run = DataContract(data_contract_str=_mode_contract(), metadata_only=True).test()

    assert run.result == ResultEnum.passed
    assert run.dryRun is False
    skipped = [c for c in run.checks if c.result == ResultEnum.skipped]
    assert {c.type for c in skipped} == _ROW_CHECK_TYPES
    assert all(c.reason == "Row-value check disabled by --metadata-only" for c in skipped)
    assert {c.type for c in run.checks if c.result == ResultEnum.passed} == {
        "model_exists",
        "field_is_present",
        "field_type",
    }
    assert connection.executed
    connection.close.assert_called_once()


@pytest.mark.parametrize("severity, expected", [("warning", ResultEnum.warning), ("critical", ResultEnum.failed)])
def test_hana_contract_applies_data_checks_and_quality_severity(monkeypatch, severity, expected):
    connection = DataConnection("view")
    connection.insert([(1, 1, "OPEN"), (2, 1, "PAID")])
    monkeypatch.setattr("datacontract.engines.hana.check_hana_execute.get_connection", lambda server: connection)
    contract = OpenDataContractStandard.model_validate_json(_mode_contract())
    contract.schema_[0].properties = [
        SchemaProperty(name="id", physicalName="ID", logicalType="number", primaryKey=True),
        SchemaProperty(
            name="status",
            physicalName="STATUS",
            logicalType="string",
            required=True,
            enum=[{"value": "OPEN"}, {"value": "PAID"}],
        ),
    ]
    contract.schema_[0].quality = [DataQuality(metric="rowCount", mustBe=0, severity=severity)]
    contract.slaProperties = None

    run = DataContract(data_contract_str=contract.model_dump_json(by_alias=True, exclude_none=True)).test()

    assert run.result == expected
    assert {check.type for check in run.checks if check.result == expected} == {"row_count"}
    assert {check.type for check in run.checks if check.result == ResultEnum.passed} >= {
        "field_type",
        "field_primary_key_required",
        "field_primary_key_unique",
        "field_required",
        "field_enum",
    }
    assert all(check.result in (ResultEnum.passed, expected) for check in run.checks)


def test_hana_dry_run_cli_needs_no_driver_or_credentials(monkeypatch, tmp_path):
    monkeypatch.delenv("DATACONTRACT_HANA_USERNAME", raising=False)
    monkeypatch.delenv("DATACONTRACT_HANA_PASSWORD", raising=False)
    import_driver = Mock(side_effect=AssertionError("A dry run must not import hdbcli"))
    monkeypatch.setattr("datacontract.engines.hana.hana_connection.import_hdbcli", import_driver)
    path = tmp_path / "hana.yaml"
    path.write_text(_mode_contract())

    result = CliRunner().invoke(app, ["test", str(path), "--dry-run"])

    assert result.exit_code == 0, result.stdout
    assert "skipped" in result.stdout
    import_driver.assert_not_called()


def test_hana_metadata_only_still_detects_catalog_mismatches(monkeypatch):
    connection = FakeConnection(catalog_response([column("ID", "NVARCHAR")]))
    connection.close = Mock()
    monkeypatch.setattr("datacontract.engines.hana.check_hana_execute.get_connection", lambda server: connection)

    run = DataContract(data_contract_str=_mode_contract(), metadata_only=True).test()

    assert run.result == ResultEnum.failed
    assert any(c.type == "field_type" and c.field == "ID" and c.result == ResultEnum.failed for c in run.checks)
    assert any(
        c.type == "field_is_present" and c.field == "STATUS" and c.result == ResultEnum.failed for c in run.checks
    )
    assert all("SYS." in sql for sql, _ in connection.executed)


_required_hana_env = [
    "DATACONTRACT_HANA_HOST",
    "DATACONTRACT_HANA_SCHEMA",
    "DATACONTRACT_HANA_USERNAME",
    "DATACONTRACT_HANA_PASSWORD",
]
hana_integration = pytest.mark.skipif(
    any(os.environ.get(name) is None for name in _required_hana_env),
    reason="SAP HANA Cloud integration environment variables are not set.",
)


@hana_integration
def test_hana_full_contract_pass():
    run = DataContract(data_contract_file="fixtures/hana/datacontract_hana_basic.yaml").test()

    assert run.result in (ResultEnum.passed, ResultEnum.warning)
    assert not any(check.result in (ResultEnum.failed, ResultEnum.error) for check in run.checks)


@hana_integration
def test_hana_full_contract_fail_schema():
    run = DataContract(data_contract_file="fixtures/hana/datacontract_hana_fail_schema.yaml").test()

    assert run.result == ResultEnum.failed
    assert all(check.engine == "hana" for check in run.checks)


@hana_integration
def test_hana_quality_check_live():
    run = DataContract(data_contract_file="fixtures/hana/datacontract_hana_quality.yaml").test()

    assert all(check.engine == "hana" for check in run.checks)
