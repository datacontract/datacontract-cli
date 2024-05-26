import logging

import yaml
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract

logging.basicConfig(level=logging.DEBUG, force=True)


def test_cli():
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "import",
            "--format",
            "avro",
            "--source",
            "fixtures/avro/data/orders.avsc",
        ],
    )
    assert result.exit_code == 0


def test_import_avro_schema():
    result = DataContract().import_from_source("avro", "fixtures/avro/data/orders.avsc")

    expected = """
dataContractSpecification: 0.9.3
id: my-data-contract-id
info:
  title: My Data Contract
  version: 0.0.1
models:
  orders:
    description: My Model
    namespace: com.sample.schema
    fields:
      ordertime:
        type: long
        description: My Field
        required: true
      orderid:
        type: int
        required: true
      itemid:
        type: string
        required: true
      material:
        type: string
        required: false
        description: An optional field
      orderunits:
        type: double
        required: true
      emailadresses:
        type: array
        description: Different email adresses of a customer
        items:
           type: string
           format: email
           pattern: ^.*@.*$
        required: true
      address:
        type: object
        required: true
        fields:
          city:
            type: string
            required: true
          state:
            type: string
            required: true
          zipcode:
            type: long
            required: true
    """
    print("Result:\n", result.to_yaml())
    assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected)
    assert DataContract(data_contract_str=expected).lint(enabled_linters="none").has_passed()


def test_import_avro_arrays_of_records_and_nested_arrays():
    result = DataContract().import_from_source("avro", "fixtures/avro/data/arrays.avsc")

    expected = """
dataContractSpecification: 0.9.3
id: my-data-contract-id
info:
  title: My Data Contract
  version: 0.0.1
models:
  orders:
    description: My Model
    fields:
      orderid:
        type: int
        required: true
      adresses:
        type: array
        required: true
        description: Adresses of a customer
        items:
          type: object
          fields:
            city:
              type: string
              required: true
            state:
              type: string
              required: true
            zipcode:
              type: long
              required: true
      nestedArrays:
        type: array
        required: true
        description: Example schema for an array of arrays
        items:
          type: array
          items:
            type: int
      nationalities:
        type: array
        required: false
        items:
          type: string
"""
    print("Result:\n", result.to_yaml())
    assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected)
    assert DataContract(data_contract_str=expected).lint(enabled_linters="none").has_passed()


def test_import_avro_nested_records():
    result = DataContract().import_from_source("avro", "fixtures/avro/data/nested.avsc")

    expected = """
dataContractSpecification: 0.9.3
id: my-data-contract-id
info:
  title: My Data Contract
  version: 0.0.1
models:
  Doc:
    namespace: com.xxx
    fields:
      fieldA:
        type: long
        required: false
      fieldB:
        type: record
        required: false
        fields:
          fieldC:
            type: string
            required: false
"""
    print("Result:\n", result.to_yaml())
    assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected)
    assert DataContract(data_contract_str=expected).lint(enabled_linters="none").has_passed()


def test_import_avro_nested_records_with_arrays():
    result = DataContract().import_from_source("avro", "fixtures/avro/data/nested_with_arrays.avsc")

    expected = """
dataContractSpecification: 0.9.3
id: my-data-contract-id
info:
  title: My Data Contract
  version: 0.0.1
models:
  MarketingLoyaltyAggregation:
    namespace: domain.schemas
    fields:
      Entries:
        type: array
        required: true
        items:
          type: object
          fields:
            Identifier:
              type: string
              required: true
            BranchPromo:
              type: record
              required: false
              fields:
                CodePrefix:
                  type: int
                  required: true
                Criteria:
                  type: object
                  required: true
                  fields:
                    MinimumSpendThreshold:
                      type: double
                      required: false
                    ApplicableBranchIDs:
                      type: array
                      required: false
                      items: 
                        type: string
                    ProductGroupDetails:
                      type: record
                      required: false
                      fields:
                        IncludesAlcohol:
                          type: boolean
                          required: true
                        ItemList:
                          type: array
                          required: false
                          items:
                            type: object
                            fields:
                              ProductID:
                                type: string
                                required: true
                              IsPromoItem:
                                type: boolean
                                required: false
"""
    print("Result:\n", result.to_yaml())
    assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected)
    assert DataContract(data_contract_str=expected).lint(enabled_linters="none").has_passed()


def test_import_avro_logicalTypes():
    result = DataContract().import_from_source("avro", "fixtures/avro/data/logicalTypes.avsc")

    expected = """
dataContractSpecification: 0.9.3
id: my-data-contract-id
info:
  title: My Data Contract
  version: 0.0.1
models:
  Test:
    namespace: mynamespace.com
    fields:
      test_id:
        type: string
        required: true
        description: id documentation test
      device_id:
        type: int
        required: true
      test_value:
        type: double
        required: true
      num_items:
        type: int
        required: true
      processed_timestamp:
        type: long
        required: true
        description: 'The date the event was processed: for more info https://avro.apache.org/docs/current/spec.html#Local+timestamp+%28microsecond+precision%29'        
        config:
          avroLogicalType: local-timestamp-micros
      description:
        type: string
        required: true
      is_processed:
        type: boolean
        required: true
        config:
          avroDefault: false 
"""
    print("Result:\n", result.to_yaml())
    assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected)
    assert DataContract(data_contract_str=expected).lint(enabled_linters="none").has_passed()
