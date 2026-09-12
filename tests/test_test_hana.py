import os

import pytest
from open_data_contract_standard.model import OpenDataContractStandard, SchemaObject, SchemaProperty, Server

from datacontract.data_contract import DataContract
from datacontract.engines.data_contract_test import execute_data_contract_test
from datacontract.model.run import Check, ResultEnum, Run


def test_hana_test_flow_bypasses_soda(monkeypatch):
    from datacontract.engines.hana import check_hana_execute as hana_module

    def fake_check_hana_execute(run, data_contract, server, schema_name="all", check_categories=None):
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
