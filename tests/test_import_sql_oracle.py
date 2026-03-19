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
apiVersion: v3.1.0
kind: DataContract
id: my-data-contract
name: My Data Contract
version: 1.0.0
status: draft
servers:
  - server: oracle
    type: oracle
schema:
  - name: field_showcase
    physicalType: table
    logicalType: object
    physicalName: field_showcase
    properties:
      - name: field_primary_key
        logicalType: integer
        physicalType: INT
        primaryKey: true
        primaryKeyPosition: 1
        description: Primary key
      - name: field_not_null
        logicalType: integer
        physicalType: INT
        required: true
        description: Not null
      - name: field_varchar
        logicalType: string
        physicalType: VARCHAR2
        description: Variable-length string
      - name: field_nvarchar
        logicalType: string
        physicalType: NVARCHAR2
        description: Variable-length Unicode string
      - name: field_number
        logicalType: number
        physicalType: NUMBER
        description: Number
      - name: field_float
        logicalType: number
        physicalType: FLOAT
        description: Float
      - name: field_date
        logicalType: date
        physicalType: DATE
        description: Date and Time down to second precision
      - name: field_binary_float
        logicalType: number
        physicalType: FLOAT
        description: 32-bit floating point number
      - name: field_binary_double
        logicalType: number
        physicalType: DOUBLE PRECISION
        description: 64-bit floating point number
      - name: field_timestamp
        logicalType: date
        physicalType: TIMESTAMP
        description: Timestamp with fractional second precision of 6, no timezones
      - name: field_timestamp_tz
        logicalType: date
        physicalType: TIMESTAMP WITH TIME ZONE
        description: Timestamp with fractional second precision of 6, with timezones (TZ)
      - name: field_timestamp_ltz
        logicalType: date
        physicalType: TIMESTAMPLTZ
        description: Timestamp with fractional second precision of 6, with local timezone (LTZ)
      - name: field_interval_year
        logicalType: object
        physicalType: INTERVAL YEAR TO MONTH
        description: Interval of time in years and months with default (2) precision
      - name: field_interval_day
        logicalType: object
        physicalType: INTERVAL DAY TO SECOND
        description: Interval of time in days, hours, minutes and seconds with default (2 / 6) precision
      - name: field_raw
        logicalType: array
        physicalType: RAW
        description: Large raw binary data
      - name: field_rowid
        logicalType: object
        physicalType: ROWID
        description: Base 64 string representing a unique row address
      - name: field_urowid
        logicalType: object
        physicalType: UROWID
        description: Base 64 string representing the logical address
      - name: field_char
        logicalType: string
        logicalTypeOptions:
          maxLength: 10
        physicalType: CHAR(10)
        description: Fixed-length string
      - name: field_nchar
        logicalType: string
        logicalTypeOptions:
          maxLength: 10
        physicalType: NCHAR(10)
        description: Fixed-length Unicode string
      - name: field_clob
        logicalType: string
        physicalType: CLOB
        description: Character large object
      - name: field_nclob
        logicalType: string
        physicalType: NCLOB
        description: National character large object
      - name: field_blob
        logicalType: array
        physicalType: BLOB
        description: Binary large object
      - name: field_bfile
        logicalType: array
        physicalType: BFILE
    """
    print("Result", result.to_yaml())
    assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected)


def test_import_sql_constraints():
    result = DataContract.import_from_source("sql", "fixtures/postgres/data/data_constraints.sql", dialect="postgres")

    expected = """
apiVersion: v3.1.0
kind: DataContract
id: my-data-contract
name: My Data Contract
version: 1.0.0
status: draft
servers:
  - server: postgres
    type: postgres
schema:
  - name: customer_location
    physicalType: table
    logicalType: object
    physicalName: customer_location
    properties:
      - name: id
        logicalType: number
        physicalType: DECIMAL
        required: true
      - name: created_by
        logicalType: string
        logicalTypeOptions:
          maxLength: 30
        physicalType: VARCHAR(30)
        required: true
      - name: create_date
        logicalType: date
        physicalType: TIMESTAMP
        required: true
      - name: changed_by
        logicalType: string
        logicalTypeOptions:
          maxLength: 30
        physicalType: VARCHAR(30)
      - name: change_date
        logicalType: date
        physicalType: TIMESTAMP
      - name: name
        logicalType: string
        logicalTypeOptions:
          maxLength: 120
        physicalType: VARCHAR(120)
        required: true
      - name: short_name
        logicalType: string
        logicalTypeOptions:
          maxLength: 60
        physicalType: VARCHAR(60)
      - name: display_name
        logicalType: string
        logicalTypeOptions:
          maxLength: 120
        physicalType: VARCHAR(120)
        required: true
      - name: code
        logicalType: string
        logicalTypeOptions:
          maxLength: 30
        physicalType: VARCHAR(30)
        required: true
      - name: description
        logicalType: string
        logicalTypeOptions:
          maxLength: 4000
        physicalType: VARCHAR(4000)
      - name: language_id
        logicalType: number
        physicalType: DECIMAL
        required: true
      - name: status
        logicalType: string
        logicalTypeOptions:
          maxLength: 2
        physicalType: VARCHAR(2)
        required: true
    """
    print("Result", result.to_yaml())
    assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected)


def test_import_sql_oracle_number_precision_in_custom_properties():
    """Test that Oracle NUMBER(p, s) types store precision/scale in customProperties, not logicalTypeOptions."""
    result = DataContract.import_from_source(
        "sql", "fixtures/oracle/import/ddl_with_precision.sql", dialect="oracle"
    )

    expected = """
apiVersion: v3.1.0
kind: DataContract
id: my-data-contract
name: My Data Contract
version: 1.0.0
status: draft
servers:
  - server: oracle
    type: oracle
schema:
  - name: customers
    physicalType: table
    logicalType: object
    physicalName: customers
    properties:
      - name: customer_id
        logicalType: number
        physicalType: NUMBER(9, 0)
        description: Integer-like number with precision
      - name: customer_score
        logicalType: number
        physicalType: NUMBER(5, 2)
        description: Decimal number with precision and scale
      - name: balance
        logicalType: number
        physicalType: NUMBER(15, 4)
        description: Large decimal number
      - name: amount
        logicalType: number
        physicalType: NUMBER(10)
        description: Number with only precision
      - name: plain_number
        logicalType: number
        physicalType: NUMBER
        description: Plain number without precision or scale
    """
    print("Result", result.to_yaml())
    assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected)

    # Verify precision and scale are NOT in logicalTypeOptions (which would violate ODCS schema)
    parsed = yaml.safe_load(result.to_yaml())
    for prop in parsed["schema"][0]["properties"]:
        log_type_opts = prop.get("logicalTypeOptions", {})
        assert "precision" not in log_type_opts, f"precision must not be in logicalTypeOptions for {prop['name']}"
        assert "scale" not in log_type_opts, f"scale must not be in logicalTypeOptions for {prop['name']}"
