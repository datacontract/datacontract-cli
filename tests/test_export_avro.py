import json

from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.export.avro_converter import to_avro_schema_json
from datacontract.model.data_contract_specification import DataContractSpecification

# logging.basicConfig(level=logging.DEBUG, force=True)


def test_cli():
    runner = CliRunner()
    result = runner.invoke(app, ["export", "./fixtures/avro/export/datacontract.yaml", "--format", "avro"])
    assert result.exit_code == 0


def test_to_avro_schema():
    data_contract = DataContractSpecification.from_file("fixtures/avro/export/datacontract.yaml")
    with open("fixtures/avro/export/orders_with_datefields.avsc") as file:
        expected_avro_schema = file.read()

    model_name, model = next(iter(data_contract.models.items()))
    result = to_avro_schema_json(model_name, model)

    assert json.loads(result) == json.loads(expected_avro_schema)


def test_to_avro_schema_with_logical_types():
    data_contract = DataContractSpecification.from_file("fixtures/avro/export/datacontract_logicalType.yaml")
    with open("fixtures/avro/export/datacontract_logicalType.avsc") as file:
        expected_avro_schema = file.read()

    model_name, model = next(iter(data_contract.models.items()))
    result = to_avro_schema_json(model_name, model)

    assert json.loads(result) == json.loads(expected_avro_schema)


def test_to_avro_schema_with_required():
    data_contract = DataContractSpecification.from_file("fixtures/avro/export/datacontract_test_required.yaml")
    with open("fixtures/avro/export/datacontract_test_required.avsc") as file:
        expected_avro_schema = file.read()

    model_name, model = next(iter(data_contract.models.items()))
    result = to_avro_schema_json(model_name, model)

    assert json.loads(result) == json.loads(expected_avro_schema)


def test_to_avro_schema_enum():
    data_contract = DataContractSpecification.from_file("fixtures/avro/export/datacontract_enum.yaml")
    with open("fixtures/avro/export/datacontract_enum.avsc") as file:
        expected_avro_schema = file.read()

    model_name, model = next(iter(data_contract.models.items()))
    result = to_avro_schema_json(model_name, model)

    assert json.loads(result) == json.loads(expected_avro_schema)


def test_to_decimal_type():
    data_contract = DataContractSpecification.from_file("fixtures/avro/export/datacontract_decimal.yaml")
    with open("fixtures/avro/export/datacontract_decimal.avsc") as file:
        expected_avro_schema = file.read()

    model_name, model = next(iter(data_contract.models.items()))
    result = to_avro_schema_json(model_name, model)

    assert json.loads(result) == json.loads(expected_avro_schema)
