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
    result = DataContract().import_from_source(format="parquet", source=parquet_file_path)

    expected = """dataContractSpecification: 1.1.0
id: my-data-contract-id
info:
  title: My Data Contract
  version: 0.0.1
models:
  combined_no_time:
    fields:
      string_field:
        type: string
      blob_field:
        type: bytes
      boolean_field:
        type: boolean
      decimal_field:
        type: decimal
        precision: 10
        scale: 2
      float_field:
        type: float
      double_field:
        type: double
      integer_field:
        type: int
      bigint_field:
        type: long
      struct_field:
        type: struct
      array_field:
        type: array
      list_field:
        type: array
      map_field:
        type: map
      date_field:
        type: date
      timestamp_field:
        type: timestamp
"""

    assert result.to_yaml() == expected
    assert DataContract(data_contract_str=expected).lint(enabled_linters=set()).has_passed()
