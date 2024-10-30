from datacontract.data_contract import DataContract

# parquet_file_path = "fixtures/parquet/data/combined.parquet"  # todo use combined example
parquet_file_path = "fixtures/parquet/data/string.parquet"


def test_cli():
    """TODO"""


def test_import_parquet():
    result = DataContract().import_from_source(format="parquet", source=parquet_file_path)

    expected = """dataContractSpecification: 1.1.0
id: my-data-contract-id
info:
  title: My Data Contract
  version: 0.0.1
models:
  string:
    fields:
      string_field:
        type: string
"""

    assert result.to_yaml() == expected
    assert DataContract(data_contract_str=expected).lint(enabled_linters=set()).has_passed()
