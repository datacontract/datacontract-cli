import json
import logging

from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.export.avro_converter import to_avro_schema_json
from datacontract.model.data_contract_specification import DataContractSpecification

logging.basicConfig(level=logging.DEBUG, force=True)


def test_cli():
    runner = CliRunner()
    result = runner.invoke(app, ["export", "./fixtures/kafka-avro-remote/datacontract.yaml", "--format", "avro"])
    assert result.exit_code == 0


def test_to_avro_schema():
    data_contract = DataContractSpecification.from_file("fixtures/kafka-avro-remote/datacontract.yaml")
    expected_avro_schema = """
    {
  "fields": [
    {
      "name": "ordertime",
      "doc": "My Field",
      "type": "long"
    },
    {
      "name": "orderid",
      "type": "int"
    },
    {
      "name": "itemid",
      "type": "string"
    },
    {
      "name": "orderunits",
      "type": "double"
    },
    {
      "name": "address",
      "type": {
        "fields": [
          {
            "name": "city",
            "type": "string"
          },
          {
            "name": "state",
            "type": "string"
          },
          {
            "name": "zipcode",
            "type": "long"
          }
        ],
        "name": "address",
        "type": "record"
      }
    }
  ],
  "name": "orders",
  "namespace": "com.example.checkout",
  "doc": "My Model",
  "type": "record"
}
"""

    model_name, model = next(iter(data_contract.models.items()))
    result = to_avro_schema_json(model_name, model)

    assert json.loads(result) == json.loads(expected_avro_schema)


def test_to_avro_schema_with_logicalTypes():
    data_contract = DataContractSpecification.from_file("fixtures/kafka-avro-remote/datacontract_logicalType.yaml")
    expected_avro_schema = """
  {
  "type": "record",
  "name": "Test",
  "namespace": "mynamespace.com",
  "fields": [
    {
      "name": "test_id",
      "doc": "id documentation test",
      "type": "string"
    },
    {
      "name": "device_id",
      "type": "int"
    },
    {
      "name": "test_value",
      "type": "double"
    },
    {
      "name": "num_items",
      "type": "int"
    },
    {
      "name": "processed_timestamp",
      "doc": "The date the event was processed: for more info https://avro.apache.org/docs/current/spec.html#Local+timestamp+%28microsecond+precision%29",
      "logicalType": "local-timestamp-micros",
      "type": "long"
    },
    {
      "name": "description",
      "type": "string"
    },
    {
      "name": "is_processed",
      "type": "boolean",
      "default": false
    }
  ]
}
"""

    model_name, model = next(iter(data_contract.models.items()))
    result = to_avro_schema_json(model_name, model)

    assert json.loads(result) == json.loads(expected_avro_schema)
