import json

from datacontract_specification.model import DataContractSpecification
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.export.avro_exporter import to_avro_schema_json
from datacontract.imports.dcs_importer import convert_dcs_to_odcs

# logging.basicConfig(level=logging.DEBUG, force=True)


def test_cli():
    runner = CliRunner()
    result = runner.invoke(app, ["export", "./fixtures/avro/export/datacontract.yaml", "--format", "avro"])
    assert result.exit_code == 0


def test_to_avro_schema():
    dcs = DataContractSpecification.from_file("fixtures/avro/export/datacontract.yaml")
    data_contract = convert_dcs_to_odcs(dcs)
    with open("fixtures/avro/export/orders_with_datefields.avsc") as file:
        expected_avro_schema = file.read()

    model = data_contract.schema_[0]
    result = to_avro_schema_json(model.name, model)

    assert json.loads(result) == json.loads(expected_avro_schema)


def test_to_avro_schema_with_logical_types():
    dcs = DataContractSpecification.from_file("fixtures/avro/export/datacontract_logicalType.yaml")
    data_contract = convert_dcs_to_odcs(dcs)
    with open("fixtures/avro/export/datacontract_logicalType.avsc") as file:
        expected_avro_schema = file.read()

    model = data_contract.schema_[0]
    result = to_avro_schema_json(model.name, model)

    assert json.loads(result) == json.loads(expected_avro_schema)


def test_to_avro_schema_with_required():
    dcs = DataContractSpecification.from_file("fixtures/avro/export/datacontract_test_required.yaml")
    data_contract = convert_dcs_to_odcs(dcs)
    with open("fixtures/avro/export/datacontract_test_required.avsc") as file:
        expected_avro_schema = file.read()

    model = data_contract.schema_[0]
    result = to_avro_schema_json(model.name, model)

    assert json.loads(result) == json.loads(expected_avro_schema)


def test_to_avro_schema_enum():
    dcs = DataContractSpecification.from_file("fixtures/avro/export/datacontract_enum.yaml")
    data_contract = convert_dcs_to_odcs(dcs)
    with open("fixtures/avro/export/datacontract_enum.avsc") as file:
        expected_avro_schema = file.read()

    model = data_contract.schema_[0]
    result = to_avro_schema_json(model.name, model)

    assert json.loads(result) == json.loads(expected_avro_schema)


def test_to_decimal_type():
    dcs = DataContractSpecification.from_file("fixtures/avro/export/datacontract_decimal.yaml")
    data_contract = convert_dcs_to_odcs(dcs)
    with open("fixtures/avro/export/datacontract_decimal.avsc") as file:
        expected_avro_schema = file.read()

    model = data_contract.schema_[0]
    result = to_avro_schema_json(model.name, model)

    assert json.loads(result) == json.loads(expected_avro_schema)


def test_to_field_namespace():
    dcs = DataContractSpecification.from_file("fixtures/avro/export/datacontract_test_field_namespace.yaml")
    data_contract = convert_dcs_to_odcs(dcs)
    with open("fixtures/avro/export/datacontract_test_field_namespace.avsc") as file:
        expected_avro_schema = file.read()

    model = data_contract.schema_[0]
    result = to_avro_schema_json(model.name, model)

    assert json.loads(result) == json.loads(expected_avro_schema)


def test_to_field_map():
    dcs = DataContractSpecification.from_file("fixtures/avro/export/datacontract_test_field_map.yaml")
    data_contract = convert_dcs_to_odcs(dcs)
    with open("fixtures/avro/export/datacontract_test_field_map.avsc") as file:
        expected_avro_schema = file.read()

    model = data_contract.schema_[0]
    result = to_avro_schema_json(model.name, model)

    assert json.loads(result) == json.loads(expected_avro_schema)


def test_to_field_float():
    dcs = DataContractSpecification.from_file("fixtures/avro/export/datacontract_test_field_float.yaml")
    data_contract = convert_dcs_to_odcs(dcs)
    with open("fixtures/avro/export/datacontract_test_field_float.avsc") as file:
        expected_avro_schema = file.read()

    model = data_contract.schema_[0]
    result = to_avro_schema_json(model.name, model)

    assert json.loads(result) == json.loads(expected_avro_schema)
