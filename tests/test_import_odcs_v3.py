import os
import sys

import yaml
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract

# logging.basicConfig(level=logging.DEBUG, force=True)


def test_cli():
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "import",
            "--format",
            "odcs",
            "--source",
            "./fixtures/odcs_v3/full-example.odcs.yaml",
        ],
    )
    assert result.exit_code == 0


def test_import_full_odcs():
    result = DataContract.import_from_source("odcs", "./fixtures/odcs_v3/full-example.odcs.yaml")
    expected_datacontract = read_file("fixtures/odcs_v3/full-example.datacontract.yml")
    assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected_datacontract)
    assert DataContract(data_contract_str=expected_datacontract).lint().has_passed()


def test_import_complex_odcs():
    result = DataContract.import_from_source("odcs", "./fixtures/odcs_v3/adventureworks.odcs.yaml")
    expected_datacontract = read_file("fixtures/odcs_v3/adventureworks.datacontract.yml")
    assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected_datacontract)
    assert DataContract(data_contract_str=expected_datacontract).lint().has_passed()


def test_import_odcs_without_logicaltype():
    """Test that fields without logicalType are imported using physicalType as fallback.

    This test validates the fix for issue #891 where fields without logicalType
    were being discarded during import, even though logicalType is optional per ODCS spec.
    """
    odcs_yaml = """
version: 3.0.2
kind: DataContract
apiVersion: v3.0.2
id: test-contract-no-logicaltype
name: Test Contract Without LogicalType
description:
  purpose: Test ODCS import without logicalType

schema:
  - name: test_table
    type: table
    properties:
      - name: event_date
        physicalType: DATE
        description: Event date without logicalType
        required: true
      - name: amount
        physicalType: DECIMAL(10,2)
        description: Amount without logicalType
        required: true
      - name: status
        physicalType: VARCHAR(50)
        description: Status field
        required: false
      - name: count
        physicalType: INTEGER
        description: Count field
"""

    # Write test file
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(odcs_yaml)
        temp_file = f.name

    try:
        result = DataContract.import_from_source("odcs", temp_file)

        # Verify model was imported
        assert result.models is not None
        assert "test_table" in result.models

        # Verify all fields were imported (not discarded)
        model = result.models["test_table"]
        assert len(model.fields) == 4, f"Expected 4 fields, got {len(model.fields)}"

        # Verify field types were correctly mapped from physicalType
        assert "event_date" in model.fields
        assert model.fields["event_date"].type == "date"

        assert "amount" in model.fields
        assert model.fields["amount"].type == "decimal"

        assert "status" in model.fields
        assert model.fields["status"].type == "varchar"

        assert "count" in model.fields
        assert model.fields["count"].type == "integer"

        # Verify physicalType is preserved in config
        assert model.fields["amount"].config is not None
        assert model.fields["amount"].config.get("physicalType") == "DECIMAL(10,2)"

    finally:
        # Clean up temp file
        os.unlink(temp_file)


def read_file(file):
    if not os.path.exists(file):
        print(f"The file '{file}' does not exist.")
        sys.exit(1)
    with open(file, "r") as file:
        file_content = file.read()
    return file_content
