import json
import logging
import os
import sys

from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.export.avro_converter import to_avro_schema_json
from datacontract.model.data_contract_specification import \
    DataContractSpecification

logging.basicConfig(level=logging.DEBUG, force=True)


def test_cli():
    runner = CliRunner()
    result = runner.invoke(app, [
        "export",
        "./examples/kafka-avro-remote/datacontract.yaml",
        "--format", "avro"
    ])
    assert result.exit_code == 0


def test_to_avro_schema():
    data_contract = DataContractSpecification.from_file("./examples/kafka-avro-remote/datacontract.yaml")
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
  "doc": "My Model",
  "type": "record"
}
"""

    model_name, model = next(iter(data_contract.models.items()))
    result = to_avro_schema_json(model_name, model)

    assert json.loads(result) == json.loads(expected_avro_schema)


def read_file(data_contract_file):
    if not os.path.exists(data_contract_file):
        print(f"The file '{data_contract_file}' does not exist.")
        sys.exit(1)
    with open(data_contract_file, 'r') as file:
        file_content = file.read()
    return file_content
