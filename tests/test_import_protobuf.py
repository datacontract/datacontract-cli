import yaml
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract

# logging.basicConfig(level=logging.DEBUG, force=True)

protobuf_file_path = "fixtures/protobuf/data/sample_data.proto3.data"
nested_imports_c_proto = "fixtures/protobuf/nested_imports/C.proto"
nested_imports_subdirs_main = "fixtures/protobuf/nested_imports_subdirs/main.proto"


def test_cli():
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "import",
            "--format",
            "protobuf",
            "--source",
            protobuf_file_path,
        ],
    )
    assert result.exit_code == 0


def test_import_protobuf():
    result = DataContract.import_from_source("protobuf", protobuf_file_path)

    expected = """dataContractSpecification: 1.2.1
id: my-data-contract-id
info:
  title: My Data Contract
  version: 0.0.1
models:
  Product:
    description: Details of Product.
    type: table
    fields:
      id:
        description: Field id
        type: string
        required: false
      name:
        description: Field name
        type: string
        required: false
      price:
        description: Field price
        type: double
        required: false
      category:
        description: Enum field category
        type: string
        values:
          CATEGORY_UNKNOWN: 0
          CATEGORY_ELECTRONICS: 1
          CATEGORY_CLOTHING: 2
          CATEGORY_HOME_APPLIANCES: 3
        required: false
      tags:
        description: Field tags
        type: string
        required: false
      reviews:
        description: List of Review
        type: array
        items:
          type: object
          fields:
            user:
              description: Field user
              type: string
              required: false
            rating:
              description: Field rating
              type: integer
              required: false
            comment:
              description: Field comment
              type: string
              required: false
  Review:
    description: Details of Review.
    type: table
    fields:
      user:
        description: Field user
        type: string
        required: false
      rating:
        description: Field rating
        type: integer
        required: false
      comment:
        description: Field comment
        type: string
        required: false
"""

    print("Result", result.to_yaml())
    assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected)
    # Disable linters so we don't get "missing description" warnings
    assert DataContract(data_contract_str=expected).lint().has_passed()


def test_import_protobuf_nested_imports():
    """
    Test transitive imports: C.proto imports A.proto which imports B.proto.
    C.proto -> A.proto -> B.proto

    This tests that when importing C.proto, the importer correctly resolves
    the transitive dependency on B.proto through A.proto.

    See: https://github.com/datacontract/datacontract-cli/issues/943
    """
    result = DataContract.import_from_source("protobuf", nested_imports_c_proto)

    expected = """dataContractSpecification: 1.2.1
id: my-data-contract-id
info:
  title: My Data Contract
  version: 0.0.1
models:
  Company:
    description: Details of Company.
    type: table
    fields:
      name:
        description: Field name
        type: string
        required: false
      registration_number:
        description: Field registration_number
        type: string
        required: false
      contact:
        description: Nested object of Person
        type: object
        fields:
          name:
            description: Field name
            type: string
            required: false
          email:
            description: Field email
            type: string
            required: false
          address:
            description: Nested object of Address
            type: object
            fields:
              street:
                description: Field street
                type: string
                required: false
              city:
                description: Field city
                type: string
                required: false
              country:
                description: Field country
                type: string
                required: false
              postal_code:
                description: Field postal_code
                type: string
                required: false
"""

    print("Result", result.to_yaml())
    assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected)


def test_import_protobuf_nested_imports_subdirs():
    """
    Test transitive imports across subdirectories:
    main.proto imports models/person.proto which imports common/address.proto.
    main.proto -> models/person.proto -> common/address.proto

    This tests that when importing main.proto, the importer correctly resolves
    the transitive dependency on common/address.proto through models/person.proto.

    See: https://github.com/datacontract/datacontract-cli/issues/943
    """
    result = DataContract.import_from_source("protobuf", nested_imports_subdirs_main)

    expected = """dataContractSpecification: 1.2.1
id: my-data-contract-id
info:
  title: My Data Contract
  version: 0.0.1
models:
  Company:
    description: Details of Company.
    type: table
    fields:
      name:
        description: Field name
        type: string
        required: false
      registration_number:
        description: Field registration_number
        type: string
        required: false
      contact:
        description: Nested object of Person
        type: object
        fields:
          name:
            description: Field name
            type: string
            required: false
          email:
            description: Field email
            type: string
            required: false
          address:
            description: Nested object of Address
            type: object
            fields:
              street:
                description: Field street
                type: string
                required: false
              city:
                description: Field city
                type: string
                required: false
              country:
                description: Field country
                type: string
                required: false
              postal_code:
                description: Field postal_code
                type: string
                required: false
"""

    print("Result", result.to_yaml())
    assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected)
