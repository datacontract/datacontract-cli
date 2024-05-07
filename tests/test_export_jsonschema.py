import json
import logging
import os
import sys

from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.export.jsonschema_converter import to_jsonschemas
from datacontract.model.data_contract_specification import DataContractSpecification

logging.basicConfig(level=logging.DEBUG, force=True)


def test_cli():
    runner = CliRunner()
    result = runner.invoke(app, ["export", "./fixtures/local-json/datacontract.yaml", "--format", "jsonschema"])
    assert result.exit_code == 0


def test_to_jsonschemas():
    data_contract_file = "fixtures/local-json/datacontract.yaml"
    file_content = read_file(data_contract_file=data_contract_file)
    data_contract = DataContractSpecification.from_string(file_content)
    expected_json_schema = """{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "Statistik_Code": {
      "type": "integer"
    },
    "Statistik_Label": {
      "type": "string"
    },
    "Zeit_Code": {
      "type": "string"
    },
    "Zeit_Label": {
      "type": "string"
    },
    "Zeit": {
      "type": "integer"
    },
    "1_Merkmal_Code": {
      "type": "string"
    },
    "1_Merkmal_Label": {
      "type": "string"
    },
    "1_Auspraegung_Code": {
      "type": "string",
      "enum": ["DG"]
    },
    "1_Auspraegung_Label": {
      "type": "string",
      "enum": ["Deutschland"]
    },
    "2_Merkmal_Code": {
      "type": "string",
      "enum": ["MONAT"]
    },
    "2_Merkmal_Label": {
      "type": "string"
    },
    "2_Auspraegung_Code": {
      "type": "string"
    },
    "2_Auspraegung_Label": {
      "type": "string"
    },
    "PREIS1__Verbraucherpreisindex__2020=100": {
      "type": "string"
    },
    "PREIS1__Verbraucherpreisindex__q": {
      "type": "string"
    },
    "Verbraucherpreisindex__CH0004": {
      "type": ["string", "null"]
    },
    "Verbraucherpreisindex__CH0004__q": {
      "type": "string"
    },
    "PREIS1__CH0005": {
      "type": ["string", "null"]
    },
    "PREIS1__CH0005__q": {
      "type": "string"
    }
  },
  "required": [
    "Statistik_Code",
    "Statistik_Label",
    "Zeit_Code",
    "Zeit_Label",
    "Zeit",
    "1_Merkmal_Code",
    "1_Merkmal_Label",
    "1_Auspraegung_Code",
    "1_Auspraegung_Label",
    "2_Merkmal_Code",
    "2_Merkmal_Label",
    "2_Auspraegung_Code",
    "2_Auspraegung_Label",
    "PREIS1__Verbraucherpreisindex__2020=100",
    "PREIS1__Verbraucherpreisindex__q",
    "Verbraucherpreisindex__CH0004__q",
    "PREIS1__CH0005__q"
  ]
}
"""

    result = to_jsonschemas(data_contract)
    assert result["verbraucherpreisindex"] == json.loads(expected_json_schema)


def test_to_jsonschemas_complex():
    data_contract_file = "fixtures/local-json-complex/datacontract.yaml"
    file_content = read_file(data_contract_file=data_contract_file)
    data_contract = DataContractSpecification.from_string(file_content)
    expected_json_schema = """{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
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
              "type": [
                "object",
                "null"
              ],
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
    }
  },
  "required": [
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
