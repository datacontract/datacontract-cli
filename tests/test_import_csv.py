import yaml
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract

# logging.basicConfig(level=logging.DEBUG, force=True)

csv_file_path = "fixtures/csv/data/sample_data.csv"


def test_cli():
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "import",
            "--format",
            "csv",
            "--source",
            csv_file_path,
        ],
    )
    assert result.exit_code == 0


def test_import_csv():
    source = "fixtures/csv/data/sample_data_5_column.csv"
    result = DataContract.import_from_source("csv", source)

    # Access schema via ODCS structure (schema_ due to Pydantic naming conflict)
    schema = result.schema_[0]
    assert schema is not None
    properties = {p.name: p for p in schema.properties}
    assert len(properties["field_one"].examples) == 5
    assert len(properties["field_two"].examples) > 0
    assert len(properties["field_three"].examples) > 0
    assert properties["field_four"].examples is None
    assert properties["field_five"].examples is None

    # Clear examples for comparison
    for p in schema.properties:
        p.examples = None

    expected = f"""version: 1.0.0
kind: DataContract
apiVersion: v3.1.0
id: my-data-contract
name: My Data Contract
status: draft
servers:
- server: production
  type: local
  customProperties:
  - property: delimiter
    value: ','
  format: csv
  path: {source}
schema:
- name: sample_data_5_column
  physicalType: table
  description: Generated model of fixtures/csv/data/sample_data_5_column.csv
  logicalType: object
  physicalName: sample_data_5_column
  properties:
  - name: field_one
    physicalType: VARCHAR
    logicalType: string
    required: true
    unique: true
  - name: field_two
    physicalType: INTEGER
    logicalType: integer
    logicalTypeOptions:
      minimum: 14.0
      maximum: 89.0
    required: true
  - name: field_three
    physicalType: VARCHAR
    logicalType: date
    unique: true
  - name: field_four
    physicalType: VARCHAR
    logicalType: string
  - name: field_five
    physicalType: BOOLEAN
    logicalType: boolean
    required: true
  - name: field_six
    physicalType: VARCHAR
    customProperties:
    - property: format
      value: email
    logicalType: string
    """
    print("Result", result.to_yaml())
    assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected)
