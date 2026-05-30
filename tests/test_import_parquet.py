import os
import tempfile

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
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
    customProperties:
    - property: precision
      value: 10
    - property: scale
      value: 2
    logicalType: number
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


@pytest.mark.parametrize(
    "field_name, arrow_type, expected_logical, expected_physical",
    [
        ("large_string_field", pa.large_string(), "string", "LARGE_STRING"),
        ("large_binary_field", pa.large_binary(), "bytes", "LARGE_BINARY"),
        ("large_list_field", pa.large_list(pa.int32()), "array", "LARGE_LIST"),
        ("half_float_field", pa.float16(), "number", "HALF_FLOAT"),
        ("time32_field", pa.time32("s"), "time", "TIME"),
        ("time64_field", pa.time64("us"), "time", "TIME"),
        ("duration_field", pa.duration("s"), "string", "DURATION"),
        ("fixed_size_binary_field", pa.binary(16), "bytes", "FIXED_SIZE_BINARY(16)"),
        ("fixed_size_list_field", pa.list_(pa.int32(), 4), "array", "FIXED_SIZE_LIST"),
    ],
)
def test_import_parquet_large_types(field_name, arrow_type, expected_logical, expected_physical):
    """Test that large and extended PyArrow types are imported without raising an exception."""
    schema = pa.schema([pa.field(field_name, arrow_type)])
    table = pa.table({field_name: pa.array([], type=arrow_type)}, schema=schema)

    with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        pq.write_table(table, tmp_path)
        result = DataContract.import_from_source(format="parquet", source=tmp_path)
        schema_obj = result.schema_[0]
        prop = schema_obj.properties[0]
        assert prop.logicalType == expected_logical, f"Expected logicalType={expected_logical}, got {prop.logicalType}"
        assert prop.physicalType == expected_physical, (
            f"Expected physicalType={expected_physical}, got {prop.physicalType}"
        )
    finally:
        os.unlink(tmp_path)
