import pytest
import sqlalchemy
from oracledb import DatabaseError
from testcontainers.oracle import OracleDbContainer

from datacontract.data_contract import DataContract
from tests.dcs_deprecation import assert_dcs_deprecation_is_the_only_warning, without_dcs_deprecation

oracleContainer = OracleDbContainer("gvenzl/oracle-free:slim-faststart")
ORACLE_SERVER_PORT: int = 1521


@pytest.fixture(scope="module", autouse=True)
def oracle_container(request):
    oracleContainer.start()

    def remove_container():
        oracleContainer.stop()

    request.addfinalizer(remove_container)


def test_test_oracle_contract_dcs(oracle_container, monkeypatch):
    monkeypatch.setenv("DATACONTRACT_ORACLE_USERNAME", "SYSTEM")
    monkeypatch.setenv("DATACONTRACT_ORACLE_PASSWORD", oracleContainer.oracle_password)

    _init_sql("fixtures/oracle/data/testcase.sql")

    data_contract_str = _setup_datacontract("fixtures/oracle/datacontract-oracle-dcs.yaml")
    data_contract = DataContract(data_contract_str=data_contract_str)

    run = data_contract.test()

    print(run)
    assert_dcs_deprecation_is_the_only_warning(run)
    assert all(check.result == "passed" for check in without_dcs_deprecation(run))


def test_test_oracle_contract_odcs(oracle_container, monkeypatch):
    monkeypatch.setenv("DATACONTRACT_ORACLE_USERNAME", "SYSTEM")
    monkeypatch.setenv("DATACONTRACT_ORACLE_PASSWORD", oracleContainer.oracle_password)

    _init_sql("fixtures/oracle/data/testcase.sql")

    data_contract_str = _setup_datacontract("fixtures/oracle/datacontract-oracle-odcs.yaml")
    data_contract = DataContract(data_contract_str=data_contract_str)

    run = data_contract.test()

    print(run)
    assert run.result == "passed"
    assert all(check.result == "passed" for check in run.checks)


def test_test_oracle_wrong_physical_type_fails(oracle_container, monkeypatch):
    """A physicalType is only checked when the catalog is read: one that differs
    from the column must fail, not fall back to a passing logicalType check."""
    monkeypatch.setenv("DATACONTRACT_ORACLE_USERNAME", "SYSTEM")
    monkeypatch.setenv("DATACONTRACT_ORACLE_PASSWORD", oracleContainer.oracle_password)

    _init_sql("fixtures/oracle/data/testcase.sql")

    data_contract_str = _setup_datacontract("fixtures/oracle/datacontract-oracle-odcs.yaml").replace(
        "logicalType: string\n        physicalType: VARCHAR2\n",
        "logicalType: string\n        physicalType: NVARCHAR2\n",
        1,
    )
    assert "physicalType: VARCHAR2" not in data_contract_str.split("DESCRIPTION", 1)[1].split("AMOUNT", 1)[0]

    run = DataContract(data_contract_str=data_contract_str).test()

    failed = {check.name: check.reason for check in run.checks if check.result != "passed"}
    assert list(failed) == ["Check that field DESCRIPTION has physical type NVARCHAR2"]
    assert "but the column is 'VARCHAR2" in failed["Check that field DESCRIPTION has physical type NVARCHAR2"]


def _init_sql(sql_file_path):
    with sqlalchemy.create_engine(oracleContainer.get_connection_url()).begin() as engine:
        with engine.connection.cursor() as cursor:
            with open(sql_file_path, "r") as sql_file:
                for sql_command in sql_file.read().split(";"):
                    try:
                        cursor.execute(sql_command)
                    except DatabaseError as e:
                        print(f"Error executing SQL command: {e}", sql_command)


def _setup_datacontract(datacontract):
    with open(datacontract) as data_contract_file:
        data_contract_str = data_contract_file.read()
    port = oracleContainer.get_exposed_port(ORACLE_SERVER_PORT)
    data_contract_str = data_contract_str.replace("__PORT__", str(port))
    return data_contract_str


def test_catalog_views_are_checked_like_tables(oracle_container, monkeypatch):
    monkeypatch.setenv("DATACONTRACT_ORACLE_USERNAME", "SYSTEM")
    monkeypatch.setenv("DATACONTRACT_ORACLE_PASSWORD", oracleContainer.oracle_password)
    _init_sql("fixtures/oracle/data/testcase.sql")
    with sqlalchemy.create_engine(oracleContainer.get_connection_url()).begin() as connection:
        connection.exec_driver_sql("BEGIN DBMS_STATS.GATHER_TABLE_STATS('SYSTEM', 'CHECKS_TESTCASE'); END;")
    contract = f"""apiVersion: v3.1.0
kind: DataContract
id: oracle-catalog
name: Oracle catalog
version: 1.0.0
status: active
servers:
  - server: catalog
    type: oracle
    host: localhost
    port: {oracleContainer.get_exposed_port(ORACLE_SERVER_PORT)}
    serviceName: FREEPDB1
    schema: SYS
schema:
  - name: ALL_TABLES
    quality:
      - type: sql
        description: Every table of the SYSTEM user has statistics from the last week
        query: |
          SELECT COUNT(*) FROM ALL_TABLES
          WHERE OWNER = 'SYSTEM' AND TABLE_NAME = 'CHECKS_TESTCASE' AND (LAST_ANALYZED IS NULL OR LAST_ANALYZED < SYSDATE - 7)
        mustBe: 0
    properties:
      - name: TABLE_NAME
        logicalType: string
        required: true
      - name: NUM_ROWS
        logicalType: integer
        logicalTypeOptions:
          maximum: 100000000
"""

    run = DataContract(data_contract_str=contract).test()

    assert run.result == "passed", [(c.name, c.reason) for c in run.checks if c.result != "passed"]
