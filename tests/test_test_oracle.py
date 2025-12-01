import pytest
import sqlalchemy
from oracledb import DatabaseError
from testcontainers.oracle import OracleDbContainer

from datacontract.data_contract import DataContract

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
    assert run.result == "passed"
    assert all(check.result == "passed" for check in run.checks)


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
