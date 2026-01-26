import yaml

from datacontract.data_contract import DataContract

sql_file_path = "fixtures/snowflake/import/ddl.sql"


def test_import_sql_snowflake():
    result = DataContract().import_from_source("sql", sql_file_path, dialect="snowflake")

    expected = """version: 1.0.0
kind: DataContract
apiVersion: v3.1.0
id: my-data-contract
name: My Data Contract
status: draft
servers:
- server: snowflake
  type: snowflake
schema:
- name: my_table
  physicalType: table
  description: My Comment
  logicalType: object
  physicalName: my_table
  properties:
  - name: field_primary_key
    physicalType: DECIMAL(38, 0)
    description: Primary key
    logicalType: number
    logicalTypeOptions:
      precision: 38
      scale: 0
    required: true
  - name: field_not_null
    physicalType: INT
    description: Not null
    logicalType: integer
    required: true
  - name: field_char
    physicalType: CHAR(10)
    description: Fixed-length string
    logicalType: string
    logicalTypeOptions:
      maxLength: 10
  - name: field_character
    physicalType: CHAR(10)
    description: Fixed-length string
    logicalType: string
    logicalTypeOptions:
      maxLength: 10
  - name: field_varchar
    physicalType: VARCHAR(100)
    description: Variable-length string
    tags:
    - SNOWFLAKE.CORE.PRIVACY_CATEGORY='IDENTIFIER'
    - SNOWFLAKE.CORE.SEMANTIC_CATEGORY='NAME'
    logicalType: string
    logicalTypeOptions:
      maxLength: 100
  - name: field_text
    physicalType: VARCHAR
    description: Large variable-length string
    logicalType: string
  - name: field_string
    physicalType: VARCHAR
    description: Large variable-length Unicode string
    logicalType: string
  - name: field_tinyint
    physicalType: TINYINT
    description: Integer (0-255)
    logicalType: integer
  - name: field_smallint
    physicalType: SMALLINT
    description: Integer (-32,768 to 32,767)
    logicalType: integer
  - name: field_int
    physicalType: INT
    description: Integer (-2.1B to 2.1B)
    logicalType: integer
  - name: field_integer
    physicalType: INT
    description: Integer full name(-2.1B to 2.1B)
    logicalType: integer
  - name: field_bigint
    physicalType: BIGINT
    description: Large integer (-9 quintillion to 9 quintillion)
    logicalType: integer
  - name: field_decimal
    physicalType: DECIMAL(10, 2)
    description: Fixed precision decimal
    logicalType: number
    logicalTypeOptions:
      precision: 10
      scale: 2
  - name: field_numeric
    physicalType: DECIMAL(10, 2)
    description: Same as DECIMAL
    logicalType: number
    logicalTypeOptions:
      precision: 10
      scale: 2
  - name: field_float
    physicalType: DOUBLE
    description: Approximate floating-point
    logicalType: number
  - name: field_float4
    physicalType: FLOAT
    description: Approximate floating-point 4
    logicalType: number
  - name: field_float8
    physicalType: DOUBLE
    description: Approximate floating-point 8
    logicalType: number
  - name: field_real
    physicalType: FLOAT
    description: Smaller floating-point
    logicalType: number
  - name: field_boulean
    physicalType: BOOLEAN
    description: Boolean-like (0 or 1)
    logicalType: boolean
  - name: field_date
    physicalType: DATE
    description: Date only (YYYY-MM-DD)
    logicalType: date
  - name: field_time
    physicalType: TIME
    description: Time only (HH:MM:SS)
    logicalType: string
  - name: field_timestamp
    physicalType: TIMESTAMP
    description: More precise datetime
    logicalType: timestamp
  - name: field_timestamp_ltz
    physicalType: TIMESTAMPLTZ
    description: More precise datetime with local time zone; time zone, if provided,
      isn`t stored.
    logicalType: timestamp
  - name: field_timestamp_ntz
    physicalType: TIMESTAMPNTZ
    description: More precise datetime with no time zone; time zone, if provided,
      isn`t stored.
    logicalType: timestamp
  - name: field_timestamp_tz
    description: More precise datetime with time zone.
    logicalType: timestamp
    physicalType: 'TIMESTAMPTZ'
  - name: field_binary
    physicalType: BINARY(16)
    description: Fixed-length binary
    logicalType: object
  - name: field_varbinary
    physicalType: VARBINARY(100)
    description: Variable-length binary
    logicalType: object
  - name: field_variant
    physicalType: VARIANT
    description: VARIANT data
    logicalType: object
  - name: field_json
    physicalType: OBJECT
    description: JSON (Stored as text)
    logicalType: object"""

    print("Result", result.to_yaml())
    assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected)
    # Disable linters so we don't get "missing description" warnings account, db, schema name are required
    #assert DataContract(data_contract_str=expected).lint().has_passed()
