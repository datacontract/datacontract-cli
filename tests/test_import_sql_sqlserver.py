import yaml

from datacontract.data_contract import DataContract

sql_file_path = "fixtures/sqlserver/import/ddl.sql"


def test_import_sql_sqlserver():
    result = DataContract().import_from_source("sql", sql_file_path, dialect="sqlserver")

    expected = """
dataContractSpecification: 1.1.0
id: my-data-contract-id
info:
  title: My Data Contract
  version: 0.0.1
servers:
  sqlserver:
    type: sqlserver
models:
  my_table:
    type: table
    fields:
      field_primary_key:
        type: int
        primaryKey: true
        description: Primary key
        config:
          sqlserverType: INTEGER
      field_not_null:
        type: int
        required: true
        description: Not null
        config:
          sqlserverType: INTEGER
      field_char:
        type: string
        maxLength: 10
        description: Fixed-length string
        config:
          sqlserverType: CHAR(10)
      field_varchar:
        type: string
        maxLength: 100
        description: Variable-length string
        config:
          sqlserverType: VARCHAR(100)
      field_text:
        type: string
        description: Large variable-length string
        config:
          sqlserverType: VARCHAR(MAX)
      field_nchar:
        type: string
        maxLength: 10
        description: Fixed-length Unicode string
        config:
            sqlserverType: NCHAR(10)
      field_nvarchar:
        type: string
        maxLength: 100
        description: Variable-length Unicode string
        config:
          sqlserverType: NVARCHAR(100)
      field_ntext:
        type: string
        description: Large variable-length Unicode string
        config:
          sqlserverType: NVARCHAR(MAX)        
      field_tinyint:
        type: int
        description: Integer (0-255)
        config:
            sqlserverType: TINYINT
      field_smallint:
        type: int
        description: Integer (-32,768 to 32,767)
        config:
            sqlserverType: SMALLINT
      field_int:
        type: int
        description: Integer (-2.1B to 2.1B)
        config:
            sqlserverType: INTEGER
      field_bigint:
        type: long
        description: Large integer (-9 quintillion to 9 quintillion)
        config:
            sqlserverType: BIGINT
      field_decimal:
        type: decimal        
        precision: 10
        scale: 2
        description: Fixed precision decimal
        config:
            sqlserverType: NUMERIC(10, 2)
      field_numeric:
        type: decimal
        precision: 10
        scale: 2
        description: Same as DECIMAL
        config:
            sqlserverType: NUMERIC(10, 2)
      field_float:
        type: float
        description: Approximate floating-point
        config:
            sqlserverType: FLOAT
      field_real:
        type: float
        description: Smaller floating-point
        config:
            sqlserverType: FLOAT
      field_bit:
        type: boolean
        description: Boolean-like (0 or 1)
        config:
            sqlserverType: BIT
      field_date:
        type: date
        description: Date only (YYYY-MM-DD)
        config:
            sqlserverType: DATE
      field_time:
        type: string
        description: Time only (HH:MM:SS)
        config:
            sqlserverType: TIME        
      field_datetime2:
        type: timestamp_ntz
        description: More precise datetime
        config:
            sqlserverType: DATETIME2
      field_smalldatetime:
        type: timestamp_ntz
        description: Less precise datetime
        config:
            sqlserverType: SMALLDATETIME
      field_datetimeoffset:
        type: timestamp_tz
        description: Datetime with time zone
        config:
            sqlserverType: DATETIMEOFFSET
      field_binary:
        type: bytes
        description: Fixed-length binary
        config:
            sqlserverType: BINARY(16)
      field_varbinary:
        type: bytes
        description: Variable-length binary
        config:
            sqlserverType: VARBINARY(100)
      field_uniqueidentifier:
        type: string
        description: GUID
        config:
            sqlserverType: UNIQUEIDENTIFIER
      field_xml:
        type: string
        description: XML data
        config:
            sqlserverType: XML
      field_json:
        type: string
        description: JSON (Stored as text)
        config:
            sqlserverType: JSON
      # field_sql_variant:
      #   type: variant
      #   description: Stores different data types
      #   config:
      #       sqlserverType: SQL_VARIANT
    """
    print("Result", result.to_yaml())
    assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected)
    # Disable linters so we don't get "missing description" warnings
    assert DataContract(data_contract_str=expected).lint(enabled_linters=set()).has_passed()
