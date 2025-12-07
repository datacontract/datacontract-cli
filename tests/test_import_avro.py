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
            "avro",
            "--source",
            "fixtures/avro/data/orders.avsc",
        ],
    )
    assert result.exit_code == 0


def test_import_avro_schema():
    result = DataContract.import_from_source("avro", "fixtures/avro/data/orders.avsc")

    expected = """
version: 1.0.0
kind: DataContract
apiVersion: v3.1.0
id: my-data-contract
name: My Data Contract
status: draft
schema:
- name: orders
  physicalType: record
  description: My Model
  customProperties:
  - property: namespace
    value: com.sample.schema
  logicalType: object
  physicalName: orders
  properties:
  - name: ordertime
    physicalType: long
    description: My Field
    logicalType: integer
    required: true
  - name: orderid
    physicalType: int
    logicalType: integer
    required: true
  - name: itemid
    physicalType: string
    logicalType: string
    required: true
  - name: material
    physicalType: string
    description: An optional field
    logicalType: string
    required: false
  - name: orderunits
    physicalType: double
    logicalType: number
    required: true
  - name: emailaddresses
    physicalType: array
    description: Different email addresses of a customer
    logicalType: array
    required: true
    items:
      name: items
      physicalType: string
      logicalType: string
  - name: address
    physicalType: record
    logicalType: object
    required: true
    properties:
    - name: city
      physicalType: string
      logicalType: string
      required: true
    - name: state
      physicalType: string
      logicalType: string
      required: true
    - name: zipcode
      physicalType: long
      logicalType: integer
      required: true
  - name: status
    physicalType: enum
    description: order status
    customProperties:
    - property: avroType
      value: enum
    - property: avroSymbols
      value:
      - PLACED
      - SHIPPED
      - DELIVERED
      - CANCELLED
    logicalType: string
    required: true
  - name: metadata
    physicalType: map
    description: Additional metadata about the order
    customProperties:
    - property: avroType
      value: map
    logicalType: object
    required: true
    """
    print("Result:\n", result.to_yaml())
    assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected)


def test_import_avro_arrays_of_records_and_nested_arrays():
    result = DataContract.import_from_source("avro", "fixtures/avro/data/arrays.avsc")

    expected = """
version: 1.0.0
kind: DataContract
apiVersion: v3.1.0
id: my-data-contract
name: My Data Contract
status: draft
schema:
- name: orders
  physicalType: record
  description: My Model
  logicalType: object
  physicalName: orders
  properties:
  - name: orderid
    physicalType: int
    logicalType: integer
    required: true
  - name: addresses
    physicalType: array
    description: Addresses of a customer
    logicalType: array
    required: true
    items:
      name: items
      physicalType: record
      logicalType: object
      properties:
      - name: city
        physicalType: string
        logicalType: string
        required: true
      - name: state
        physicalType: string
        logicalType: string
        required: true
      - name: zipcode
        physicalType: long
        logicalType: integer
        required: true
  - name: nestedArrays
    physicalType: array
    description: Example schema for an array of arrays
    logicalType: array
    required: true
    items:
      name: items
      physicalType: array
      logicalType: array
      items:
        name: items
        physicalType: int
        logicalType: integer
  - name: nationalities
    physicalType: array
    logicalType: array
    required: false
    items:
      name: items
      physicalType: string
      logicalType: string
"""
    print("Result:\n", result.to_yaml())
    assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected)


def test_import_avro_nested_records():
    result = DataContract.import_from_source("avro", "fixtures/avro/data/nested.avsc")

    expected = """
version: 1.0.0
kind: DataContract
apiVersion: v3.1.0
id: my-data-contract
name: My Data Contract
status: draft
schema:
- name: Doc
  physicalType: record
  customProperties:
  - property: namespace
    value: com.xxx
  logicalType: object
  physicalName: Doc
  properties:
  - name: fieldA
    physicalType: long
    logicalType: integer
    required: false
  - name: fieldB
    physicalType: record
    logicalType: object
    required: false
    properties:
    - name: fieldC
      physicalType: string
      logicalType: string
      required: false
"""
    print("Result:\n", result.to_yaml())
    assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected)


def test_import_avro_nested_records_with_arrays():
    result = DataContract.import_from_source("avro", "fixtures/avro/data/nested_with_arrays.avsc")

    expected = """
version: 1.0.0
kind: DataContract
apiVersion: v3.1.0
id: my-data-contract
name: My Data Contract
status: draft
schema:
- name: MarketingLoyaltyAggregation
  physicalType: record
  customProperties:
  - property: namespace
    value: domain.schemas
  logicalType: object
  physicalName: MarketingLoyaltyAggregation
  properties:
  - name: Entries
    physicalType: array
    logicalType: array
    required: true
    items:
      name: items
      physicalType: record
      logicalType: object
      properties:
      - name: Identifier
        physicalType: string
        logicalType: string
        required: true
      - name: BranchPromo
        physicalType: record
        logicalType: object
        required: false
        properties:
        - name: CodePrefix
          physicalType: int
          logicalType: integer
          required: true
        - name: Criteria
          physicalType: record
          logicalType: object
          required: true
          properties:
          - name: MinimumSpendThreshold
            physicalType: double
            logicalType: number
            required: false
          - name: ApplicableBranchIDs
            physicalType: array
            logicalType: array
            required: false
            items:
              name: items
              physicalType: string
              logicalType: string
          - name: ProductGroupDetails
            physicalType: record
            logicalType: object
            required: false
            properties:
            - name: IncludesAlcohol
              physicalType: boolean
              logicalType: boolean
              required: true
            - name: ItemList
              physicalType: array
              logicalType: array
              required: false
              items:
                name: items
                physicalType: record
                logicalType: object
                properties:
                - name: ProductID
                  physicalType: string
                  logicalType: string
                  required: true
                - name: IsPromoItem
                  physicalType: boolean
                  logicalType: boolean
                  required: false
"""
    print("Result:\n", result.to_yaml())
    assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected)


def test_import_avro_logical_types():
    result = DataContract.import_from_source("avro", "fixtures/avro/data/logical_types.avsc")

    expected = """
version: 1.0.0
kind: DataContract
apiVersion: v3.1.0
id: my-data-contract
name: My Data Contract
status: draft
schema:
- name: Test
  physicalType: record
  customProperties:
  - property: namespace
    value: mynamespace.com
  logicalType: object
  physicalName: Test
  properties:
  - name: test_id
    physicalType: string
    description: id documentation test
    logicalType: string
    required: true
  - name: device_id
    physicalType: int
    logicalType: integer
    required: true
  - name: test_value
    physicalType: double
    logicalType: number
    required: true
  - name: num_items
    physicalType: int
    logicalType: integer
    required: true
  - name: processed_timestamp
    physicalType: long
    description: 'The date the event was processed: for more info https://avro.apache.org/docs/current/spec.html#Local+timestamp+%28microsecond+precision%29'
    customProperties:
    - property: avroLogicalType
      value: local-timestamp-micros
    logicalType: integer
    required: true
  - name: description
    physicalType: string
    logicalType: string
    required: true
  - name: is_processed
    physicalType: boolean
    customProperties:
    - property: avroDefault
      value: 'False'
    logicalType: boolean
    required: true
  - name: some_bytes_decimal
    physicalType: bytes
    logicalType: number
    logicalTypeOptions:
      precision: 25
      scale: 2
    required: true
"""
    print("Result:\n", result.to_yaml())
    assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected)


def test_import_avro_optional_enum():
    result = DataContract.import_from_source("avro", "fixtures/avro/data/optional_enum.avsc")

    expected = """
version: 1.0.0
kind: DataContract
apiVersion: v3.1.0
id: my-data-contract
name: My Data Contract
status: draft
schema:
- name: TestRecord
  physicalType: record
  logicalType: object
  physicalName: TestRecord
  properties:
  - name: required_enum
    physicalType: enum
    customProperties:
    - property: avroType
      value: enum
    - property: avroSymbols
      value:
      - RED
      - GREEN
      - BLUE
    logicalType: string
    required: true
  - name: optional_enum
    physicalType: enum
    customProperties:
    - property: avroType
      value: enum
    logicalType: string
    required: false
"""
    print("Result:\n", result.to_yaml())
    assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected)
