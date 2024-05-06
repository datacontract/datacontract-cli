import pytest
import yaml

from datacontract.export.sodacl_converter import to_sodacl_yaml
from datacontract.lint import resolve
from datacontract.model.data_contract_specification import DataContractSpecification


@pytest.fixture
def check_expected() -> str:
    expected = """
        checks for orders:
          - schema:
              name: Check that field order_id is present
              fail:
                when required column missing:
                  - order_id
          - schema:
              name: Check that field order_id has type string
              fail:
                when wrong column type:
                  order_id: string
          - missing_count(order_id) = 0:
              name: Check that required field order_id has no null values 
          - schema:
              name: Check that field processed_timestamp is present
              fail:
                when required column missing:
                  - processed_timestamp
          - schema:
              name: Check that field processed_timestamp has type timestamp
              fail:
                when wrong column type:
                  processed_timestamp: timestamp
          - missing_count(processed_timestamp) = 0:
              name: Check that required field processed_timestamp has no null values 
          - freshness(processed_timestamp) < 1d
          - row_count > 10
        checks for line_items:
          - row_count > 10:
              name: Have at lease 10 line items
        """
    return expected


def test_to_sodacl(check_expected: str):
    data_contract_specification_str = """
dataContractSpecification: 0.9.1
models:
  orders:
    description: test
    fields:
      order_id:
        type: string
        required: true
      processed_timestamp:
        type: timestamp
        required: true
quality:
    type: SodaCL
    specification:
      checks for orders:
         - freshness(processed_timestamp) < 1d
         - row_count > 10
      checks for line_items:
         - row_count > 10:
             name: Have at lease 10 line items
    """

    data = yaml.safe_load(data_contract_specification_str)
    data_contract_specification = DataContractSpecification(**data)

    result = to_sodacl_yaml(data_contract_specification)

    assert yaml.safe_load(result) == yaml.safe_load(check_expected)


def test_export_sodacl(check_expected: str):
    data_contract_specification = resolve.resolve_data_contract_from_location(
        "./fixtures/sodacl/datacontract.yaml", inline_quality=True
    )

    result = to_sodacl_yaml(data_contract_specification)

    assert yaml.safe_load(result) == yaml.safe_load(check_expected)
