"""``logicalType: map`` (ODCS v3.2.0, RFC 0030): a first-class nested type across test, export and import."""

import json

import duckdb
import pytest
import yaml
from open_data_contract_standard.model import CustomProperty, MapDefinition, SchemaProperty

from datacontract.data_contract import DataContract
from datacontract.engines.checks.type_normalize import schema_property_matches, schema_property_mismatch_reason
from datacontract.export.sql_type_converter import convert_to_sql_type
from datacontract.model.map_type import get_map_key, get_map_value, is_map
from datacontract.model.run import ResultEnum

CONTRACT = """apiVersion: v3.2.0
kind: DataContract
id: orders-map
name: Orders
version: 1.0.0
status: active
servers:
  - server: production
    type: duckdb
    database: {database}
schema:
  - name: orders
    properties:
      - name: order_id
        logicalType: string
        physicalType: VARCHAR
      - name: attributes
        logicalType: map
        physicalType: MAP(VARCHAR, INTEGER)
        map:
          key:
            logicalType: string
          value:
            logicalType: integer
      - name: lines
        logicalType: map
        map:
          key:
            logicalType: string
          value:
            logicalType: object
            properties:
              - name: quantity
                logicalType: integer
              - name: unit
                logicalType: string
"""


def _map_property(**value) -> SchemaProperty:
    return SchemaProperty(
        name="attributes",
        logicalType="map",
        map=MapDefinition(key=SchemaProperty(logicalType="string"), value=SchemaProperty(**value)),
    )


# --- the helper reads the map block and the pre-3.2.0 spellings -------------------------------


def test_map_block_wins():
    prop = _map_property(logicalType="integer")
    assert is_map(prop)
    assert get_map_key(prop).logicalType == "string"
    assert get_map_value(prop).logicalType == "integer"


def test_legacy_custom_properties_are_still_read():
    prop = SchemaProperty(
        name="attributes",
        logicalType="object",
        physicalType="map",
        customProperties=[
            CustomProperty(property="mapKeyType", value="string"),
            CustomProperty(property="mapValueType", value="integer"),
        ],
    )
    assert is_map(prop)
    assert get_map_key(prop).logicalType == "string"
    assert get_map_value(prop).logicalType == "integer"

    native = SchemaProperty(
        name="attributes",
        physicalType="map",
        customProperties=[
            CustomProperty(property="mapKeys", value="VARCHAR"),
            CustomProperty(property="mapValues", value="INTEGER"),
        ],
    )
    assert get_map_key(native).physicalType == "VARCHAR"
    # a logical type keyword in the legacy value is read as such
    assert get_map_value(native).logicalType == "integer"


def test_legacy_value_fields_on_the_map_property_become_the_value():
    prop = SchemaProperty(
        name="attributes",
        physicalType="map",
        properties=[SchemaProperty(name="quantity", logicalType="integer")],
    )
    value = get_map_value(prop)
    assert value.logicalType == "object"
    assert value.properties[0].name == "quantity"


def test_not_a_map():
    prop = SchemaProperty(name="order_id", logicalType="string")
    assert not is_map(prop)
    assert get_map_key(prop) is None
    assert get_map_value(prop) is None


# --- the comparator ----------------------------------------------------------------------------


def test_map_key_and_value_are_compared():
    expected = _map_property(logicalType="integer")
    assert schema_property_matches(expected, _map_property(logicalType="integer"))
    assert not schema_property_matches(expected, _map_property(logicalType="string"))
    assert "[value]" in schema_property_mismatch_reason(expected, _map_property(logicalType="string"))
    assert "expected type 'integer' but got 'string'" in schema_property_mismatch_reason(
        expected, _map_property(logicalType="string")
    )


def test_an_object_declared_against_a_map_column_reads_as_an_untyped_object():
    # pre-3.2.0 contracts spelled maps as objects; keep the lenient behaviour for them
    declared = SchemaProperty(name="attributes", logicalType="object")
    assert schema_property_matches(declared, _map_property(logicalType="integer"))
    declared_with_fields = SchemaProperty(
        name="attributes", logicalType="object", properties=[SchemaProperty(name="a", logicalType="string")]
    )
    reason = schema_property_mismatch_reason(declared_with_fields, _map_property(logicalType="integer"))
    assert "can't be verified" in reason


# --- datacontract test against DuckDB -----------------------------------------------------------


@pytest.fixture
def orders_db(tmp_path) -> str:
    path = str(tmp_path / "orders.duckdb")
    con = duckdb.connect(path)
    con.execute(
        "CREATE TABLE orders (order_id VARCHAR, attributes MAP(VARCHAR, INTEGER), "
        "lines MAP(VARCHAR, STRUCT(quantity INTEGER, unit VARCHAR)))"
    )
    con.execute(
        "INSERT INTO orders VALUES ('1', MAP {{'a': 1}}, MAP {{'x': {{'quantity': 2, 'unit': 'pcs'}}}})".replace(
            "{{", "{"
        ).replace("}}", "}")
    )
    con.close()
    return path


def test_test_checks_map_key_and_value_types(orders_db):
    run = DataContract(data_contract_str=CONTRACT.format(database=orders_db)).test()

    print(run.pretty())
    assert run.result == ResultEnum.passed
    nested = [c for c in run.checks if c.type in ("field_nested_type", "field_type", "field_physical_type")]
    assert nested, [c.type for c in run.checks]


def test_test_fails_on_a_wrong_map_value_type(orders_db):
    contract = CONTRACT.format(database=orders_db).replace(
        "          value:\n            logicalType: integer\n", "          value:\n            logicalType: string\n"
    )

    run = DataContract(data_contract_str=contract).test()

    print(run.pretty())
    assert run.result == ResultEnum.failed
    failed = [c for c in run.checks if c.result == ResultEnum.failed]
    assert any("[value]" in (c.reason or "") for c in failed), [c.reason for c in failed]


# --- exporters ---------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "server_type, expected",
    [
        ("snowflake", "MAP(STRING, NUMBER)"),
        ("databricks", "MAP<STRING,INT>"),
        ("dataframe", "MAP<STRING,INT>"),
        ("local", "MAP(VARCHAR, INTEGER)"),
        ("clickhouse", "Map(String, Int32)"),
        ("trino", "map(varchar, integer)"),
        ("postgres", "jsonb"),
        ("mysql", "json"),
        ("sqlserver", "nvarchar(max)"),
        ("bigquery", "JSON"),
    ],
)
def test_sql_types(server_type, expected):
    assert convert_to_sql_type(_map_property(logicalType="integer"), server_type) == expected


def test_nested_map_sql_type():
    prop = _map_property(
        logicalType="map",
        map=MapDefinition(key=SchemaProperty(logicalType="string"), value=SchemaProperty(logicalType="boolean")),
    )
    assert convert_to_sql_type(prop, "local") == "MAP(VARCHAR, MAP(VARCHAR, BOOLEAN))"
    assert convert_to_sql_type(prop, "databricks") == "MAP<STRING,MAP<STRING,BOOLEAN>>"


def test_exporters_read_the_map_block():
    data_contract = DataContract(data_contract_str=CONTRACT.format(database="orders.duckdb"))

    json_schema = json.loads(data_contract.export("jsonschema"))
    attributes = json_schema["properties"]["attributes"]
    assert attributes["type"] == ["object", "null"]
    assert attributes["additionalProperties"]["type"] == ["integer", "null"]
    assert json_schema["properties"]["lines"]["additionalProperties"]["properties"]["quantity"]

    avro = json.loads(data_contract.export("avro"))
    attributes = next(f for f in avro["fields"] if f["name"] == "attributes")
    assert attributes["type"]["type"] == "map"
    assert attributes["type"]["values"] == "int"
    lines = next(f for f in avro["fields"] if f["name"] == "lines")
    assert lines["type"]["values"]["type"] == "record"

    spark = data_contract.export("spark")
    assert "MapType(" in spark and "StringType()" in spark and "LongType()" in spark

    protobuf = data_contract.export("protobuf")
    assert "map<string, int32> attributes" in protobuf

    pydantic_model = data_contract.export("pydantic-model")
    assert "dict[str, int]" in pydantic_model

    go = data_contract.export("go")
    assert "map[string]int64" in go

    sql = data_contract.export("sql", sql_server_type="databricks")
    assert "MAP<STRING,INT>" in sql

    html = data_contract.export("html")
    assert "key: string" in html and "value: integer" in html

    dcs = yaml.safe_load(data_contract.export("dcs"))
    field = dcs["models"]["orders"]["fields"]["attributes"]
    assert field["type"] == "map"
    assert field["keys"]["type"] == "string"
    assert field["values"]["type"] == "integer"

    exported = yaml.safe_load(data_contract.export("odcs"))
    assert exported["schema"][0]["properties"][1]["map"]["value"]["logicalType"] == "integer"


def test_iceberg_export_reads_the_map_block():
    data_contract = DataContract(data_contract_str=CONTRACT.format(database="orders.duckdb"))
    schema = json.loads(data_contract.export("iceberg"))
    attributes = next(f for f in schema["fields"] if f["name"] == "attributes")
    assert attributes["type"]["type"] == "map"
    assert attributes["type"]["key"] == "string"
    assert attributes["type"]["value"] == "long"


# --- importers ---------------------------------------------------------------------------------


def test_sql_import_expands_map_types(tmp_path):
    ddl = tmp_path / "orders.sql"
    ddl.write_text("CREATE TABLE orders (order_id STRING, attributes MAP<STRING, ARRAY<INT>>);")

    result = DataContract.import_from_source("sql", str(ddl), dialect="databricks")

    attributes = result.schema_[0].properties[1]
    assert attributes.logicalType == "map"
    assert attributes.physicalType.lower() == "map<string, array<int>>"
    assert attributes.map.key.logicalType == "string"
    assert attributes.map.value.logicalType == "array"
    assert attributes.map.value.items.logicalType == "integer"


def test_dcs_import_expands_map_types():
    dcs = """dataContractSpecification: 1.2.0
id: orders
info:
  title: Orders
  version: 1.0.0
models:
  orders:
    fields:
      attributes:
        type: map
        keys:
          type: string
        values:
          type: object
          fields:
            quantity:
              type: integer
"""
    result = DataContract(data_contract_str=dcs).get_data_contract()

    attributes = result.schema_[0].properties[0]
    assert attributes.logicalType == "map"
    assert attributes.map.key.logicalType == "string"
    assert attributes.map.value.logicalType == "object"
    assert attributes.map.value.properties[0].name == "quantity"
    assert attributes.customProperties is None or not any(
        cp.property.startswith("map") for cp in attributes.customProperties
    )
