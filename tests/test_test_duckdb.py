# import pytest

from pathlib import Path

import duckdb

from datacontract.data_contract import DataContract
from datacontract.model.run import ResultEnum, Run


def test_test_duckdb():
    _init_sql("fixtures/duckdb/data/data.sql")

    datacontract_file = "fixtures/duckdb/datacontract.yaml"
    data_contract_str = _setup_datacontract(datacontract_file)
    data_contract = DataContract(data_contract_str=data_contract_str)

    run: Run = data_contract.test()

    assert run.result == "passed"
    assert all(check.result == ResultEnum.passed for check in run.checks)


def _setup_datacontract(file):
    with open(file) as data_contract_file:
        data_contract_str = data_contract_file.read()
    return data_contract_str

def _init_sql(file_path):
    if (Path("fixtures/duckdb/db.duckdb").exists()):
        Path("fixtures/duckdb/db.duckdb").unlink()

    connection = duckdb.connect(database="fixtures/duckdb/db.duckdb" , read_only=False)

    with open(file_path, "r") as sql_file:
        sql_commands = sql_file.read()
        connection.sql(sql_commands)
    connection.close()
    pass
