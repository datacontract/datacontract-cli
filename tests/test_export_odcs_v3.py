import os
import sys

import yaml
from open_data_contract_standard.model import OpenDataContractStandard
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.export.odcs_v3_exporter import to_odcs_v3_yaml
from datacontract.lint.resolve import resolve_data_contract

# logging.basicConfig(level=logging.DEBUG, force=True)


def test_cli():
    runner = CliRunner()
    result = runner.invoke(app, ["export", "./fixtures/export/datacontract.odcs.yaml", "--format", "odcs"])
    assert result.exit_code == 0


def test_to_odcs():
    data_contract = resolve_data_contract(data_contract_str=read_file("fixtures/export/datacontract.odcs.yaml"))

    # Export to ODCS v3 YAML
    odcs_yaml = to_odcs_v3_yaml(data_contract)

    # Parse the result back to verify it's valid ODCS
    parsed = yaml.safe_load(odcs_yaml)

    # Verify key fields are present and correct
    assert parsed["id"] == "orders-unit-test"
    assert parsed["name"] == "Orders Unit Test"
    assert parsed["version"] == "1.0.0"
    assert parsed["status"] == "active"
    assert parsed["kind"] == "DataContract"
    assert parsed["apiVersion"] == "v3.1.0"

    # Verify schema
    assert len(parsed["schema"]) == 1
    schema = parsed["schema"][0]
    assert schema["name"] == "orders"
    assert schema["description"] == "The orders model"
    assert len(schema["properties"]) == 3

    # Verify servers
    assert len(parsed["servers"]) == 1
    server = parsed["servers"][0]
    assert server["server"] == "production"
    assert server["type"] == "snowflake"

    # Verify team
    assert parsed["team"]["name"] == "checkout"


def assert_equals_odcs_yaml_str(expected, actual):

    expected_yaml = OpenDataContractStandard.from_string(expected).to_yaml()
    print(expected_yaml)
    assert expected_yaml == actual
    assert yaml.safe_load(actual) == yaml.safe_load(expected)


def read_file(file):
    if not os.path.exists(file):
        print(f"The file '{file}' does not exist.")
        sys.exit(1)
    with open(file, "r") as file:
        file_content = file.read()
    return file_content
