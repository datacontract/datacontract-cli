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
    assert len(run.checks) == 4
    assert all(check.result == "passed" for check in run.checks)


def test_invalid():
    data_contract = DataContract(
        data_contract_file="fixtures/parquet/datacontract_invalid.yaml",
    )
    run = data_contract.test()
    print(run.pretty())
    assert run.result == "failed"
    assert len(run.checks) == 6
    assert any(check.result == "failed" for check in run.checks)
    assert any(check.reason == "Type Mismatch, Expected Type: DATE; Actual Type: varchar" for check in run.checks)


def test_timestamp():
    data_contract = DataContract(
        data_contract_file="fixtures/parquet/datacontract_timestamp.yaml",
    )
    run = data_contract.test()
    print(run.pretty())
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


def test_bit():
    data_contract = DataContract(
        data_contract_file="fixtures/parquet/datacontract_bit.yaml",
    )
    run = data_contract.test()
    print(run.pretty())
    assert run.result == "passed"


def test_blob():
    data_contract = DataContract(
        data_contract_file="fixtures/parquet/datacontract_blob.yaml",
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


def test_date():
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


def test_hugeint():
    data_contract = DataContract(
        data_contract_file="fixtures/parquet/datacontract_hugeint.yaml",
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


def test_interval():
    data_contract = DataContract(
        data_contract_file="fixtures/parquet/datacontract_interval.yaml",
    )
    run = data_contract.test()
    print(run.pretty())
    assert run.result == "passed"


def test_line_items():
    data_contract = DataContract(
        data_contract_file="fixtures/parquet/datacontract_line_items.yaml",
    )
    run = data_contract.test()
    print(run.pretty())
    assert run.result == "passed"


def test_list():
    data_contract = DataContract(
        data_contract_file="fixtures/parquet/datacontract_list.yaml",
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


def test_orders():
    data_contract = DataContract(
        data_contract_file="fixtures/parquet/datacontract_orders.yaml",
    )
    run = data_contract.test()
    print(run.pretty())
    assert run.result == "passed"


def test_smallint():
    data_contract = DataContract(
        data_contract_file="fixtures/parquet/datacontract_smallint.yaml",
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


def test_time():
    data_contract = DataContract(
        data_contract_file="fixtures/parquet/datacontract_time.yaml",
    )
    run = data_contract.test()
    print(run.pretty())
    assert run.result == "passed"


def test_tinyint():
    data_contract = DataContract(
        data_contract_file="fixtures/parquet/datacontract_tinyint.yaml",
    )
    run = data_contract.test()
    print(run.pretty())
    assert run.result == "passed"


def test_ubigint():
    data_contract = DataContract(
        data_contract_file="fixtures/parquet/datacontract_ubigint.yaml",
    )
    run = data_contract.test()
    print(run.pretty())
    assert run.result == "passed"


def test_uhugeint():
    data_contract = DataContract(
        data_contract_file="fixtures/parquet/datacontract_uhugeint.yaml",
    )
    run = data_contract.test()
    print(run.pretty())
    assert run.result == "passed"


def test_uinteger():
    data_contract = DataContract(
        data_contract_file="fixtures/parquet/datacontract_uinteger.yaml",
    )
    run = data_contract.test()
    print(run.pretty())
    assert run.result == "passed"


def test_usmallint():
    data_contract = DataContract(
        data_contract_file="fixtures/parquet/datacontract_usmallint.yaml",
    )
    run = data_contract.test()
    print(run.pretty())
    assert run.result == "passed"


def test_utinyint():
    data_contract = DataContract(
        data_contract_file="fixtures/parquet/datacontract_utinyint.yaml",
    )
    run = data_contract.test()
    print(run.pretty())
    assert run.result == "passed"


def test_uuid():
    data_contract = DataContract(
        data_contract_file="fixtures/parquet/datacontract_uuid.yaml",
    )
    run = data_contract.test()
    print(run.pretty())
    assert run.result == "passed"

