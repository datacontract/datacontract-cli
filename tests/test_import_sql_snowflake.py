import pytest
import yaml

from datacontract.data_contract import DataContract

sql_file_path = "fixtures/snowflake/import/ddl.sql"


def test_import_sql_snowflake():
    result = DataContract().import_from_source("sql", sql_file_path, dialect="snowflake")

    expected = """version: 1.0.0
kind: DataContract
apiVersion: v3.2.0
id: my-data-contract
name: My Data Contract
status: draft
servers:
- server: snowflake
  type: snowflake
  host: my_host
  port: 443
  database: my_database
  schema: PUBLIC
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
    customProperties:
    - property: precision
      value: 38
    - property: scale
      value: 0
    logicalType: number
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
    customProperties:
    - property: precision
      value: 10
    - property: scale
      value: 2
    logicalType: number
  - name: field_numeric
    physicalType: DECIMAL(10, 2)
    description: Same as DECIMAL
    customProperties:
    - property: precision
      value: 10
    - property: scale
      value: 2
    logicalType: number
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
    logicalType: time
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
    logicalType: string
    logicalTypeOptions:
      format: binary
  - name: field_varbinary
    physicalType: VARBINARY(100)
    description: Variable-length binary
    logicalType: string
    logicalTypeOptions:
      format: binary
  - name: field_variant
    physicalType: VARIANT
    description: VARIANT data
  - name: field_json
    physicalType: OBJECT
    description: JSON (Stored as text)"""

    print("Result", result.to_yaml())
    assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected)


def test_map_type_from_sql_time_with_precision():
    # TIME(9) is what Snowflake's INFORMATION_SCHEMA generates; it must map to time, not stay unmapped
    from datacontract.imports.sql_importer import map_type_from_sql

    assert map_type_from_sql("TIME(9)") == ("time", None)
    assert map_type_from_sql("time") == ("time", None)
    assert map_type_from_sql("time with time zone") == ("time", None)
    assert map_type_from_sql("timetz") == ("time", None)
    # must not swallow timestamps
    assert map_type_from_sql("timestamp(6)") == ("timestamp", None)
    assert map_type_from_sql("TIMESTAMP_NTZ(9)") == ("timestamp", None)


@pytest.mark.parametrize(
    ("ddl", "database", "schema"),
    [
        ("CREATE TABLE analytics.sales.orders (id INT);", "analytics", "sales"),
        ("CREATE TABLE sales.orders (id INT);", "my_database", "sales"),
        ("CREATE TABLE orders (id INT);", "my_database", "my_schema"),
        # the qualifier belongs to the query source, not to the created table
        ("CREATE TABLE orders AS SELECT * FROM analytics.sales.source;", "my_database", "my_schema"),
        # tables in two different places name no single server location
        ("CREATE TABLE a.b.one (id INT); CREATE TABLE c.d.two (id INT);", "my_database", "my_schema"),
        # a templated name is no more usable than the placeholder it would replace
        ("CREATE TABLE ${db}.PUBLIC.orders (id INT);", "my_database", "PUBLIC"),
        ("CREATE TABLE ${env}_DB.PUBLIC.orders (id INT);", "my_database", "PUBLIC"),
        # only created tables name the location
        ("CREATE VIEW other.x.v AS SELECT 1 AS id; CREATE TABLE a.b.orders (id INT);", "a", "b"),
    ],
)
def test_import_sql_server_location(tmp_path, ddl, database, schema):
    ddl_file = tmp_path / "ddl.sql"
    ddl_file.write_text(ddl)

    result = DataContract().import_from_source("sql", str(ddl_file), dialect="snowflake")

    server = yaml.safe_load(result.to_yaml())["servers"][0]
    assert server["database"] == database
    assert server["schema"] == schema


@pytest.mark.parametrize("dialect", ["mysql", "oracle", "bigquery", "databricks"])
def test_import_sql_server_location_only_where_the_parts_mean_database_and_schema(tmp_path, dialect):
    ddl_file = tmp_path / "ddl.sql"
    ddl_file.write_text("CREATE TABLE sales.orders (id INT);")

    result = DataContract().import_from_source("sql", str(ddl_file), dialect=dialect)

    server = yaml.safe_load(result.to_yaml())["servers"][0]
    assert server["database"] == "my_database"
    assert server["schema"] == "my_schema"
