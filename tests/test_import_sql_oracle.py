import yaml
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract

# logging.basicConfig(level=logging.DEBUG, force=True)

data_definition_file = "fixtures/oracle/import/ddl.sql"


def test_cli():
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "import",
            "--format",
            "sql",
            "--source",
            data_definition_file,
        ],
    )
    assert result.exit_code == 0


def test_import_sql_oracle():
    result = DataContract.import_from_source("sql", data_definition_file, dialect="oracle")

    expected = """
dataContractSpecification: 1.2.1
id: my-data-contract-id
info:
  title: My Data Contract
  version: 0.0.1
servers:
  oracle:
    type: oracle
models:
  field_showcase:
    type: table
    fields:
      field_primary_key:
        type: int
        primaryKey: true
        description: Primary key
        config:
          oracleType: INT
      field_not_null:
        type: int
        required: true
        description: Not null
        config:
          oracleType: INT
      field_varchar:
        type: string
        description: Variable-length string
        config:
          oracleType: VARCHAR2
      field_nvarchar:
        type: string
        description: Variable-length Unicode string
        config:
          oracleType: NVARCHAR2
      field_number:
        type: number
        description: Number
        config:
          oracleType: NUMBER
      field_float:
        type: float
        description: Float
        config:
          oracleType: FLOAT
      field_date:
        type: date
        description: Date and Time down to second precision
        config:
          oracleType: DATE
      field_binary_float:
        type: float
        description: 32-bit floating point number
        config:
          oracleType: FLOAT
      field_binary_double:
        type: double
        description: 64-bit floating point number
        config:
          oracleType: DOUBLE PRECISION
      field_timestamp:
        type: timestamp_ntz
        description: Timestamp with fractional second precision of 6, no timezones
        config:
          oracleType: TIMESTAMP
      field_timestamp_tz:
        type: timestamp_tz
        description: Timestamp with fractional second precision of 6, with timezones
          (TZ)
        config:
          oracleType: TIMESTAMP WITH TIME ZONE
      field_timestamp_ltz:
        type: timestamp_tz
        description: Timestamp with fractional second precision of 6, with local timezone
          (LTZ)
        config:
          oracleType: TIMESTAMPLTZ
      field_interval_year:
        type: variant
        description: Interval of time in years and months with default (2) precision
        config:
          oracleType: INTERVAL YEAR TO MONTH
      field_interval_day:
        type: variant
        description: Interval of time in days, hours, minutes and seconds with default
          (2 / 6) precision
        config:
          oracleType: INTERVAL DAY TO SECOND
      field_raw:
        type: bytes
        description: Large raw binary data
        config:
          oracleType: RAW
      field_rowid:
        type: variant
        description: Base 64 string representing a unique row address
        config:
          oracleType: ROWID
      field_urowid:
        type: variant
        description: Base 64 string representing the logical address
        config:
          oracleType: UROWID
      field_char:
        type: string
        description: Fixed-length string
        maxLength: 10
        config:
          oracleType: CHAR(10)
      field_nchar:
        type: string
        description: Fixed-length Unicode string
        maxLength: 10
        config:
          oracleType: NCHAR(10)
      field_clob:
        type: text
        description: Character large object
        config:
          oracleType: CLOB
      field_nclob:
        type: text
        description: National character large object
        config:
          oracleType: NCLOB
      field_blob:
        type: bytes
        description: Binary large object
        config:
          oracleType: BLOB
      field_bfile:
        type: bytes
        config:
          oracleType: BFILE
    """
    print("Result", result.to_yaml())
    assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected)
    # Disable linters so we don't get "missing description" warnings
    assert DataContract(data_contract_str=expected).lint().has_passed()


def test_import_sql_constraints():
    result = DataContract.import_from_source("sql", "fixtures/postgres/data/data_constraints.sql", dialect="postgres")

    expected = """
dataContractSpecification: 1.2.1
id: my-data-contract-id
info:
  title: My Data Contract
  version: 0.0.1
servers:
  postgres:
    type: postgres
models:
  customer_location:
    type: table
    fields:
      id:
        type: decimal
        required: true
        # primaryKey: true
        config:
          postgresType: DECIMAL
      created_by:
        type: string
        required: true
        maxLength: 30
        config:
          postgresType: VARCHAR(30)
      create_date:
        type: timestamp_ntz
        required: true
        config:
          postgresType: TIMESTAMP
      changed_by:
        type: string
        maxLength: 30
        config:
          postgresType: VARCHAR(30)
      change_date:
        type: timestamp_ntz
        config:
          postgresType: TIMESTAMP
      name:
        type: string
        required: true
        maxLength: 120
        config:
          postgresType: VARCHAR(120)
      short_name:
        type: string
        maxLength: 60
        config:
          postgresType: VARCHAR(60)
      display_name:
        type: string
        required: true
        maxLength: 120
        config:
          postgresType: VARCHAR(120)
      code:
        type: string
        required: true
        maxLength: 30
        config:
          postgresType: VARCHAR(30)
      description:
        type: string
        maxLength: 4000
        config:
          postgresType: VARCHAR(4000)
      language_id:
        type: decimal
        required: true
        config:
          postgresType: DECIMAL
      status:
        type: string
        required: true
        maxLength: 2
        config:
          postgresType: VARCHAR(2)
    """
    print("Result", result.to_yaml())
    assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected)
    # Disable linters so we don't get "missing description" warnings
    assert DataContract(data_contract_str=expected).lint().has_passed()
