import yaml

from datacontract.data_contract import DataContract

sql_file_path = "fixtures/snowflake/import/ddl.sql"


def test_import_sql_snowflake():
    result = DataContract().import_from_source("sql", sql_file_path, dialect="snowflake")

    expected = """
dataContractSpecification: 1.2.0
id: my-data-contract-id
info:
  title: My Data Contract
  version: 0.0.1
servers:
  snowflake:
    type: snowflake
models:
  my_table:
    description: My Comment
    type: table
    fields:
      field_primary_key:
        type: decimal
        required: true
        description: Primary key
        precision: 38
        scale: 0
        config:
          snowflakeType: DECIMAL(38, 0)
      field_not_null:
        type: int
        required: true
        description: Not null
        config:
          snowflakeType: INT
      field_char:
        type: string
        description: Fixed-length string
        maxLength: 10
        config:
          snowflakeType: CHAR(10)
      field_character:
        type: string
        description: Fixed-length string
        maxLength: 10
        config:
          snowflakeType: CHAR(10)
      field_varchar:
        type: string
        description: Variable-length string
        maxLength: 100
        tags: ["SNOWFLAKE.CORE.PRIVACY_CATEGORY='IDENTIFIER'", "SNOWFLAKE.CORE.SEMANTIC_CATEGORY='NAME'"]
        config:
          snowflakeType: VARCHAR(100)
      field_text:
        type: string
        description: Large variable-length string
        config:
          snowflakeType: TEXT
      field_string:
        type: string
        description: Large variable-length Unicode string
        config:
          snowflakeType: TEXT
      field_tinyint:
        type: int
        description: Integer (0-255)
        config:
          snowflakeType: TINYINT
      field_smallint:
        type: int
        description: Integer (-32,768 to 32,767)
        config:
          snowflakeType: SMALLINT
      field_int:
        type: int
        description: Integer (-2.1B to 2.1B)
        config:
          snowflakeType: INT
      field_integer:
        type: int
        description: Integer full name(-2.1B to 2.1B)
        config:
          snowflakeType: INT
      field_bigint:
        type: long
        description: Large integer (-9 quintillion to 9 quintillion)
        config:
          snowflakeType: BIGINT
      field_decimal:
        type: decimal
        description: Fixed precision decimal
        precision: 10
        scale: 2
        config:
          snowflakeType: DECIMAL(10, 2)
      field_numeric:
        type: decimal
        description: Same as DECIMAL
        precision: 10
        scale: 2
        config:
          snowflakeType: DECIMAL(10, 2)
      field_float:
        type: float
        description: Approximate floating-point
        config:
          snowflakeType: FLOAT
      field_float4:
        type: float
        description: Approximate floating-point 4
        config:
          snowflakeType: FLOAT
      field_float8:
        type: float
        description: Approximate floating-point 8
        config:
          snowflakeType: DOUBLE
      field_real:
        type: float
        description: Smaller floating-point
        config:
          snowflakeType: FLOAT
      field_boulean:
        type: boolean
        description: Boolean-like (0 or 1)
        config:
          snowflakeType: BOOLEAN
      field_date:
        type: date
        description: Date only (YYYY-MM-DD)
        config:
          snowflakeType: DATE
      field_time:
        type: string
        description: Time only (HH:MM:SS)
        config:
          snowflakeType: TIME
      field_timestamp:
        type: timestamp_ntz
        description: More precise datetime
        config:
          snowflakeType: TIMESTAMP
      field_timestamp_ltz:
        type: object
        description: More precise datetime with local time zone; time zone, if provided, isn`t stored.
        config:
          snowflakeType: TIMESTAMPLTZ
      field_timestamp_ntz:
        type: timestamp_ntz
        description: More precise datetime with no time zone; time zone, if provided, isn`t stored.
        config:
          snowflakeType: TIMESTAMPNTZ
      field_timestamp_tz:
        type: timestamp_tz
        description: More precise datetime with time zone.
        config:
          snowflakeType: TIMESTAMPTZ
      field_binary:
        type: bytes
        description: Fixed-length binary
        config:
          snowflakeType: BINARY(16)
      field_varbinary:
        type: bytes
        description: Variable-length binary
        config:
          snowflakeType: VARBINARY(100)
      field_variant:
        type: object
        description: VARIANT data
        config:
          snowflakeType: VARIANT
      field_json:
        type: object
        description: JSON (Stored as text)
        config:
          snowflakeType: OBJECT"""

    print("Result", result.to_yaml())
    assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected)
    # Disable linters so we don't get "missing description" warnings
    assert DataContract(data_contract_str=expected).lint(enabled_linters=set()).has_passed()
