import json
import os
import sys

from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract
from datacontract.export.jsonschema_converter import to_jsonschemas
from datacontract.model.data_contract_specification import DataContractSpecification

# logging.basicConfig(level=logging.DEBUG, force=True)


def test_cli():
    runner = CliRunner()
    result = runner.invoke(app, ["export", "./fixtures/local-json/datacontract.yaml", "--format", "jsonschema"])
    assert result.exit_code == 0


def test_to_jsonschemas():
    data_contract = DataContract(
        data_contract_file="fixtures/local-json/datacontract.yaml", inline_definitions=True
    ).get_data_contract_specification()

    with open("fixtures/local-json/datacontract.json") as file:
        expected_json_schema = file.read()

    result = to_jsonschemas(data_contract)
    assert result["verbraucherpreisindex"] == json.loads(expected_json_schema)


def test_to_jsonschemas_complex():
    data_contract_file = "fixtures/s3-json-complex/datacontract.yaml"
    file_content = read_file(data_contract_file=data_contract_file)
    data_contract = DataContractSpecification.from_string(file_content)
    expected_json_schema = """{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
      "specversion": {
        "type": "string"
      },
      "type": {
        "type": "string"
      },
      "source": {
        "type": "string",
        "format": "uri"
      },
      "id": {
        "type": "string"
      },
      "time": {
        "type": "string",
        "format": "date-time"
      },
      "subject": {
        "type": ["string", "null"]
      },
      "data": {
        "type": ["object", "null"],
        "properties": {
          "sku": {
            "type": "string"
          },
          "updated": {
            "type": "string",
            "format": "date-time"
          },
          "quantity": {
            "type": "integer"
          }
        },
        "required": ["sku", "updated", "quantity"]
      }
    },
    "required": ["specversion", "type", "source", "id", "time"]
}
"""

    result = to_jsonschemas(data_contract)

    assert result["inventory"] == json.loads(expected_json_schema)


def test_to_jsonschemas_complex_2():
    data_contract_file = "fixtures/local-json-complex/datacontract.yaml"
    file_content = read_file(data_contract_file=data_contract_file)
    data_contract = DataContractSpecification.from_string(file_content)
    expected_json_schema = """{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "array_test_string": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "array_test_object": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "key": {
            "type": "string"
          },
          "value": {
            "type": "string"
          }
        },
        "required": [
          "key",
          "value"
        ]
      }
    },
    "id": {
      "type": "string",
      "pattern": "^[0-9]{8}$",
      "minLength": 1,
      "maxLength": 10
    },
    "sts_data": {
      "type": "object",
      "properties": {
        "connection_test": {
          "type": "string",
          "enum": [
            "SUCCESS",
            "FAIL",
            "NULL"
          ]
        },
        "key_list": {
          "type": "object",
          "patternProperties": {
            "^[0-5]$": {
              "type": ["object", "null"],
              "properties": {
                "key": {
                  "type": "string",
                  "pattern": "^[0-9]{8}$"
                }
              },
              "required": [
                "key"
              ]
            }
          },
          "required": []
        }
      },
      "required": [
        "connection_test",
        "key_list"
      ]
    },
    "empty_object": {
      "type": ["object", "null"],
      "properties": {},
      "required": []
    }
  },
  "required": [
    "array_test_string",
    "array_test_object",
    "id",
    "sts_data"
  ]
}
"""
    result = to_jsonschemas(data_contract)
    assert result["sts_data"] == json.loads(expected_json_schema)


def read_file(data_contract_file):
    if not os.path.exists(data_contract_file):
        print(f"The file '{data_contract_file}' does not exist.")
        sys.exit(1)
    with open(data_contract_file, "r") as file:
        file_content = file.read()
    return file_content
