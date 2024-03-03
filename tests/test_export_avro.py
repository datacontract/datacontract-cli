import json
import logging
import os
import sys

from datacontract.export.avro_converter import to_avro_schema
from datacontract.model.data_contract_specification import \
    DataContractSpecification

logging.basicConfig(level=logging.DEBUG, force=True)


# def test_cli():
#     runner = CliRunner()
#     result = runner.invoke(app, [
#         "export",
#         "./examples/local-json/datacontract.yaml",
#         "--format", "jsonschema"
#     ])
#     assert result.exit_code == 0


def test_to_avro_schema():
    data_contract_file = ("./examples/kafka-avro-remote/datacontract.yaml")
    file_content = read_file(data_contract_file=data_contract_file)
    data_contract = DataContractSpecification.from_string(file_content)
    expected_avro_schema = """
    {
  "fields": [
    {
      "name": "ordertime",
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
  "type": "record"
}
"""

    model_name, model = next(iter(data_contract.models.items()))
    result = to_avro_schema(model_name, model.fields)

    assert json.loads(result) == json.loads(expected_avro_schema)


def read_file(data_contract_file):
    if not os.path.exists(data_contract_file):
        print(f"The file '{data_contract_file}' does not exist.")
        sys.exit(1)
    with open(data_contract_file, 'r') as file:
        file_content = file.read()
    return file_content
