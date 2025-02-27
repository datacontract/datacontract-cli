import pytest
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.model.run import Run
from datacontract.data_contract import DataContract
from datacontract.lint import resolve
from datacontract.engines.soda.connections.duckdb import get_duckdb_connection

runner = CliRunner()

#csv_file_path = "fixtures/csv/data/sample_data.csv"


def test_cli():
    result = runner.invoke(app,  "./fixtures/csv/data/datacontract.yaml")
    assert result.exit_code == 0



def test_local_json():
    data_contract = DataContract(data_contract_file="./fixtures/csv/data/datacontract.yaml")
    run = data_contract.test()
    print(run)
    assert run.result == "passed"

