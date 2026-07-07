import os

from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract

runner = CliRunner()


def test_valid_cli():
    current_file_path = os.path.abspath(__file__)
    print("DEBUG Current file path:" + current_file_path)

    result = runner.invoke(app, ["test", "./fixtures/parquet/datacontract.yaml"])
    assert result.exit_code == 0
    assert "Testing ./fixtures/parquet/datacontract.yaml" in result.stdout


def test_valid():
    data_contract = DataContract(
        data_contract_file="fixtures/parquet/datacontract.yaml",
        # publish=True,
    )
    run = data_contract.test()
    print(run.pretty())
    assert run.result == "passed"
    assert len(run.checks) == 24
    assert all(check.result == "passed" for check in run.checks)


def test_timestamp():
    data_contract = DataContract(
        data_contract_file="fixtures/parquet/datacontract_timestamp.yaml",
    )
    run = data_contract.test()
    print(run.pretty())
    assert run.result == "passed"


def test_timestamp_ntz():
    data_contract = DataContract(data_contract_file="fixtures/parquet/datacontract_timestamp_ntz.yaml")
    run = data_contract.test()
    print(run)
    assert run.result == "passed"


def test_decimal():
    data_contract = DataContract(
        data_contract_file="fixtures/parquet/datacontract_decimal.yaml",
    )
    run = data_contract.test()
    print(run.pretty())
    assert run.result == "passed"


def test_array():
    data_contract = DataContract(
        data_contract_file="fixtures/parquet/datacontract_array.yaml",
    )
    run = data_contract.test()
    print(run.pretty())
    assert run.result == "passed"


def test_bigint():
    data_contract = DataContract(
        data_contract_file="fixtures/parquet/datacontract_bigint.yaml",
    )
    run = data_contract.test()
    print(run.pretty())
    assert run.result == "passed"


def test_blob():
    data_contract = DataContract(
        data_contract_file="fixtures/parquet/datacontract_binary.yaml",
    )
    run = data_contract.test()
    print(run.pretty())
    assert run.result == "passed"


def test_boolean():
    data_contract = DataContract(
        data_contract_file="fixtures/parquet/datacontract_boolean.yaml",
    )
    run = data_contract.test()
    print(run.pretty())
    assert run.result == "passed"


def test_time():
    data_contract = DataContract(
        data_contract_file="fixtures/parquet/datacontract_date.yaml",
    )
    run = data_contract.test()
    print(run.pretty())
    assert run.result == "passed"


def test_double():
    data_contract = DataContract(
        data_contract_file="fixtures/parquet/datacontract_double.yaml",
    )
    run = data_contract.test()
    print(run.pretty())
    assert run.result == "passed"


def test_float():
    data_contract = DataContract(
        data_contract_file="fixtures/parquet/datacontract_float.yaml",
    )
    run = data_contract.test()
    print(run.pretty())
    assert run.result == "passed"


def test_integer():
    data_contract = DataContract(
        data_contract_file="fixtures/parquet/datacontract_integer.yaml",
    )
    run = data_contract.test()
    print(run.pretty())
    assert run.result == "passed"


def test_map():
    data_contract = DataContract(
        data_contract_file="fixtures/parquet/datacontract_map.yaml",
    )
    run = data_contract.test()
    print(run.pretty())
    assert run.result == "passed"


def test_string():
    data_contract = DataContract(
        data_contract_file="fixtures/parquet/datacontract_string.yaml",
    )
    run = data_contract.test()
    print(run.pretty())
    assert run.result == "passed"


def test_struct():
    data_contract = DataContract(
        data_contract_file="fixtures/parquet/datacontract_struct.yaml",
    )
    run = data_contract.test()
    print(run.pretty())
    assert run.result == "passed"


def test_nested_type_error_detail_message():
    data_contract = DataContract(
        data_contract_file="fixtures/parquet/datacontract_invalid_logical_types_example.yaml",
    )
    run = data_contract.test()
    assert run.result == "failed"
    for check in run.checks:
        if check.field == "values" and check.type == "field_type":
            assert check.result == "failed"
            assert check.reason == "field '[]': expected type 'string' but got 'integer'"
        elif check.field == "metadata" and check.type == "field_type":
            assert check.result == "failed"
            assert check.reason == "field 'name': expected type 'integer' but got 'string' (and 1 other error)"
