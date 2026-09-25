import os

from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract

runner = CliRunner()


def _assert_passed_except_types(run):
    # parquet is read as the contract's types, so its type checks warn
    assert run.result == "warning"
    assert all(c.result == "passed" or (c.type == "field_type" and c.result == "warning") for c in run.checks)


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
    assert len(run.checks) == 29
    _assert_passed_except_types(run)


def test_timestamp():
    data_contract = DataContract(
        data_contract_file="fixtures/parquet/datacontract_timestamp.yaml",
    )
    run = data_contract.test()
    print(run.pretty())
    _assert_passed_except_types(run)


def test_timestamp_ntz():
    data_contract = DataContract(data_contract_file="fixtures/parquet/datacontract_timestamp_ntz.yaml")
    run = data_contract.test()
    print(run)
    _assert_passed_except_types(run)


def test_decimal():
    data_contract = DataContract(
        data_contract_file="fixtures/parquet/datacontract_decimal.yaml",
    )
    run = data_contract.test()
    print(run.pretty())
    _assert_passed_except_types(run)


def test_number_without_precision():
    # logicalType number without declared precision/scale maps to DuckDB DECIMAL,
    # not the invalid raw type name "number"
    data_contract = DataContract(
        data_contract_file="fixtures/parquet/datacontract_number_no_precision.odcs.yaml",
    )
    run = data_contract.test()
    print(run.pretty())
    _assert_passed_except_types(run)


def test_array():
    data_contract = DataContract(
        data_contract_file="fixtures/parquet/datacontract_array.yaml",
    )
    run = data_contract.test()
    print(run.pretty())
    _assert_passed_except_types(run)


def test_bigint():
    data_contract = DataContract(
        data_contract_file="fixtures/parquet/datacontract_bigint.yaml",
    )
    run = data_contract.test()
    print(run.pretty())
    _assert_passed_except_types(run)


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
    _assert_passed_except_types(run)


def test_time():
    data_contract = DataContract(
        data_contract_file="fixtures/parquet/datacontract_date.yaml",
    )
    run = data_contract.test()
    print(run.pretty())
    _assert_passed_except_types(run)


def test_double():
    data_contract = DataContract(
        data_contract_file="fixtures/parquet/datacontract_double.yaml",
    )
    run = data_contract.test()
    print(run.pretty())
    _assert_passed_except_types(run)


def test_float():
    data_contract = DataContract(
        data_contract_file="fixtures/parquet/datacontract_float.yaml",
    )
    run = data_contract.test()
    print(run.pretty())
    _assert_passed_except_types(run)


def test_integer():
    data_contract = DataContract(
        data_contract_file="fixtures/parquet/datacontract_integer.yaml",
    )
    run = data_contract.test()
    print(run.pretty())
    _assert_passed_except_types(run)


def test_map():
    data_contract = DataContract(
        data_contract_file="fixtures/parquet/datacontract_map.yaml",
    )
    run = data_contract.test()
    print(run.pretty())
    _assert_passed_except_types(run)


def test_string():
    data_contract = DataContract(
        data_contract_file="fixtures/parquet/datacontract_string.yaml",
    )
    run = data_contract.test()
    print(run.pretty())
    _assert_passed_except_types(run)


def test_struct():
    data_contract = DataContract(
        data_contract_file="fixtures/parquet/datacontract_struct.yaml",
    )
    run = data_contract.test()
    print(run.pretty())
    _assert_passed_except_types(run)
