"""Tests for the SAP HANA test engine.

SAP HANA has no ibis or DuckDB backend, so the engine reads tables over SAP's
``hdbcli`` driver and materializes them into DuckDB (mirroring the MySQL path).
These tests stub ``hdbcli`` so they run in CI without a live HANA or the driver
installed: a fake ``hdbcli.dbapi.connect`` returns a cursor whose ``description``
and ``fetchall`` supply the seed rows the materialize step loads into DuckDB.
"""

import datetime
import sys
import types

import pytest

from datacontract.data_contract import DataContract
from datacontract.model.run import ResultEnum

# hdbcli cursor.description is a DBAPI 7-tuple; only the first element (name) is
# read by the engine. The rows match the model in the fixture contracts.
_DESCRIPTION = [
    ("field_one", None, None, None, None, None, None),
    ("field_two", None, None, None, None, None, None),
    ("field_three", None, None, None, None, None, None),
    ("field_four", None, None, None, None, None, None),
]

_ROWS = [
    ("CX-263-DU", 50, datetime.datetime(2023, 6, 16, 13, 12, 56), 19.99),
    ("IK-894-MN", 47, datetime.datetime(2023, 10, 8, 22, 40, 57), 42.00),
    ("ER-399-JY", 22, datetime.datetime(2023, 5, 16, 1, 8, 22), 100.50),
    ("MT-939-FH", 63, datetime.datetime(2023, 3, 15, 5, 15, 21), 7.25),
    ("LV-849-MI", 33, datetime.datetime(2023, 9, 8, 20, 8, 43), 88.88),
    ("VS-079-OH", 85, datetime.datetime(2023, 4, 15, 0, 50, 32), 12.34),
    ("DN-297-XY", 79, datetime.datetime(2023, 11, 8, 12, 55, 42), 56.78),
    ("ZE-172-FP", 14, datetime.datetime(2023, 12, 3, 18, 38, 38), 9.10),
    ("ID-840-EG", 89, datetime.datetime(2023, 10, 2, 17, 17, 58), 0.99),
    ("FK-230-KZ", 64, datetime.datetime(2023, 11, 27, 15, 21, 48), 250.00),
]


class _FakeCursor:
    def __init__(self):
        self.description = _DESCRIPTION

    def execute(self, sql):  # noqa: D401 - the fake ignores the SQL, always returns the seed rows
        self.description = _DESCRIPTION

    def fetchall(self):
        return list(_ROWS)

    def close(self):
        pass


class _FakeConnection:
    def cursor(self):
        return _FakeCursor()

    def close(self):
        pass


@pytest.fixture(autouse=True)
def stub_hdbcli(monkeypatch):
    """Inject a fake ``hdbcli`` module so the connection path runs without the driver."""
    fake_dbapi = types.ModuleType("hdbcli.dbapi")
    fake_dbapi.connect = lambda **kwargs: _FakeConnection()
    fake_hdbcli = types.ModuleType("hdbcli")
    fake_hdbcli.dbapi = fake_dbapi
    monkeypatch.setitem(sys.modules, "hdbcli", fake_hdbcli)
    monkeypatch.setitem(sys.modules, "hdbcli.dbapi", fake_dbapi)
    monkeypatch.setenv("DATACONTRACT_SAP_HANA_USERNAME", "system")
    monkeypatch.setenv("DATACONTRACT_SAP_HANA_PASSWORD", "password")


def test_test_sap_hana():
    with open("fixtures/sap-hana/datacontract.yaml") as f:
        data_contract_str = f.read()
    data_contract = DataContract(data_contract_str=data_contract_str)

    run = data_contract.test()

    print(run.pretty())
    assert run.result == "passed"
    assert all(check.result == ResultEnum.passed for check in run.checks)


def test_test_sap_hana_odcs():
    with open("fixtures/sap-hana/odcs.yaml") as f:
        data_contract_str = f.read()
    data_contract = DataContract(data_contract_str=data_contract_str)

    run = data_contract.test()

    print(run.pretty())
    assert run.result == "passed"
    assert all(check.result == ResultEnum.passed for check in run.checks)
