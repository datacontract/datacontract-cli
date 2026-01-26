import yaml

from datacontract.data_contract import DataContract

sql_file_path = "fixtures/sqlserver/import/ddl.sql"


def test_import_sql_sqlserver():
    result = DataContract.import_from_source("sql", sql_file_path, dialect="sqlserver")

    expected = """
apiVersion: v3.1.0
kind: DataContract
id: my-data-contract
name: My Data Contract
version: 1.0.0
status: draft
servers:
  - server: sqlserver
    type: sqlserver
schema:
  - name: my_table
    physicalType: table
    logicalType: object
    physicalName: my_table
    properties:
      - name: field_primary_key
        logicalType: integer
        physicalType: INTEGER
        primaryKey: true
        primaryKeyPosition: 1
        description: Primary key
      - name: field_not_null
        logicalType: integer
        physicalType: INTEGER
        required: true
        description: Not null
      - name: field_char
        logicalType: string
        logicalTypeOptions:
          maxLength: 10
        physicalType: CHAR(10)
        description: Fixed-length string
      - name: field_varchar
        logicalType: string
        logicalTypeOptions:
          maxLength: 100
        physicalType: VARCHAR(100)
        description: Variable-length string
      - name: field_text
        logicalType: string
        physicalType: VARCHAR(MAX)
        description: Large variable-length string
      - name: field_nchar
        logicalType: string
        logicalTypeOptions:
          maxLength: 10
        physicalType: NCHAR(10)
        description: Fixed-length Unicode string
      - name: field_nvarchar
        logicalType: string
        logicalTypeOptions:
          maxLength: 100
        physicalType: NVARCHAR(100)
        description: Variable-length Unicode string
      - name: field_ntext
        logicalType: string
        physicalType: NVARCHAR(MAX)
        description: Large variable-length Unicode string
      - name: field_tinyint
        logicalType: integer
        physicalType: TINYINT
        description: Integer (0-255)
      - name: field_smallint
        logicalType: integer
        physicalType: SMALLINT
        description: Integer (-32,768 to 32,767)
      - name: field_int
        logicalType: integer
        physicalType: INTEGER
        description: Integer (-2.1B to 2.1B)
      - name: field_bigint
        logicalType: integer
        physicalType: BIGINT
        description: Large integer (-9 quintillion to 9 quintillion)
      - name: field_decimal
        logicalType: number
        logicalTypeOptions:
          precision: 10
          scale: 2
        physicalType: NUMERIC(10, 2)
        description: Fixed precision decimal
      - name: field_numeric
        logicalType: number
        logicalTypeOptions:
          precision: 10
          scale: 2
        physicalType: NUMERIC(10, 2)
        description: Same as DECIMAL
      - name: field_float
        logicalType: number
        physicalType: FLOAT
        description: Approximate floating-point
      - name: field_real
        logicalType: number
        physicalType: FLOAT
        description: Smaller floating-point
      - name: field_bit
        logicalType: boolean
        physicalType: BIT
        description: Boolean-like (0 or 1)
      - name: field_date
        logicalType: date
        physicalType: DATE
        description: Date only (YYYY-MM-DD)
      - name: field_time
        logicalType: string
        physicalType: TIME
        description: Time only (HH:MM:SS)
      - name: field_datetime2
        logicalType: date
        physicalType: DATETIME2
        description: More precise datetime
      - name: field_smalldatetime
        logicalType: date
        physicalType: SMALLDATETIME
        description: Less precise datetime
      - name: field_datetimeoffset
        logicalType: date
        physicalType: DATETIMEOFFSET
        description: Datetime with time zone
      - name: field_binary
        logicalType: array
        physicalType: BINARY(16)
        description: Fixed-length binary
      - name: field_varbinary
        logicalType: array
        physicalType: VARBINARY(100)
        description: Variable-length binary
      - name: field_uniqueidentifier
        logicalType: string
        physicalType: UNIQUEIDENTIFIER
        description: GUID
      - name: field_xml
        logicalType: string
        physicalType: XML
        description: XML data
      - name: field_json
        logicalType: object
        physicalType: JSON
        description: JSON (Stored as text)
    """
    print("Result", result.to_yaml())
    assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected)
