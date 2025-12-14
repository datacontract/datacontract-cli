from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract

parquet_file_path = "fixtures/parquet/data/combined_no_time.parquet"


def test_cli():
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "import",
            "--format",
            "parquet",
            "--source",
            parquet_file_path,
        ],
    )
    assert result.exit_code == 0


def test_import_parquet():
    result = DataContract.import_from_source(format="parquet", source=parquet_file_path)

    expected = """version: 1.0.0
kind: DataContract
apiVersion: v3.1.0
id: my-data-contract
name: My Data Contract
status: draft
schema:
- name: combined_no_time
  physicalType: parquet
  logicalType: object
  physicalName: combined_no_time
  properties:
  - name: string_field
    physicalType: STRING
    logicalType: string
  - name: blob_field
    physicalType: BINARY
    logicalType: array
  - name: boolean_field
    physicalType: BOOLEAN
    logicalType: boolean
  - name: decimal_field
    physicalType: DECIMAL
    logicalType: number
    logicalTypeOptions:
      precision: 10
      scale: 2
  - name: float_field
    physicalType: FLOAT
    logicalType: number
  - name: double_field
    physicalType: DOUBLE
    logicalType: number
  - name: integer_field
    physicalType: INT32
    logicalType: integer
  - name: bigint_field
    physicalType: INT64
    logicalType: integer
  - name: struct_field
    physicalType: STRUCT
    logicalType: object
  - name: array_field
    physicalType: LIST
    logicalType: array
  - name: list_field
    physicalType: LIST
    logicalType: array
  - name: map_field
    physicalType: MAP
    logicalType: object
  - name: date_field
    physicalType: DATE
    logicalType: date
  - name: timestamp_field
    physicalType: TIMESTAMP
    logicalType: timestamp
"""

    assert result.to_yaml() == expected
