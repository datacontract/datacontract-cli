import logging

import pytest
import yaml
from open_data_contract_standard.model import OpenDataContractStandard, SchemaObject, SchemaProperty, Server
from pyspark.sql import SparkSession, types
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract
from datacontract.engines.data_contract_checks import check_property_type, create_checks
from datacontract.export.sql_type_converter import convert_to_databricks, convert_to_dataframe


@pytest.fixture(scope="session")
def spark(tmp_path_factory) -> SparkSession:
    """Create and configure a Spark session."""

    spark = (
        SparkSession.builder.appName("datacontract-dataframe-unittest")
        .master("local[*]")  # always force a new session
        .config(
            "spark.sql.warehouse.dir",
            f"{tmp_path_factory.mktemp('spark')}/spark-warehouse",
        )
        .config("spark.driver.host", "127.0.0.1")
        .config("spark.driver.bindAddress", "127.0.0.1")
        .config("spark.streaming.stopGracefullyOnShutdown", "true")
        .config(
            "spark.jars.packages",
            "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.5,org.apache.spark:spark-avro_2.12:3.5.5",
        )
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")
    print(f"Using PySpark version {spark.version}")
    return spark


@pytest.fixture()
def user_datacontract_desc():
    with open("fixtures/spark/import/users_datacontract_desc.yml", "r") as f:
        data_contract_str = f.read()
    return data_contract_str


@pytest.fixture()
def user_datacontract_no_desc():
    with open("fixtures/spark/import/users_datacontract_no_desc.yml", "r") as f:
        data_contract_str = f.read()
    return data_contract_str


@pytest.fixture()
def user_row():
    return {
        "id": "1",
        "name": "John Doe",
        "address": {
            "number": 123,
            "street": "Maple Street",
            "city": "Anytown",
        },
        "tags": ["tag1", "tag2"],
        "metadata": {
            "my-source-metadata": {
                "value": "1234567890",
                "type": "STRING",
                "timestamp": 1646053400,
                "source": "my-source",
            }
        },
    }


@pytest.fixture()
def user_schema():
    return types.StructType(
        [
            types.StructField("id", types.StringType()),
            types.StructField("name", types.StringType(), True, {"comment": "First and last name of the customer"}),
            types.StructField(
                "address",
                types.StructType(
                    [
                        types.StructField("number", types.IntegerType()),
                        types.StructField("street", types.StringType()),
                        types.StructField("city", types.StringType()),
                    ]
                ),
            ),
            types.StructField("tags", types.ArrayType(types.StringType())),
            types.StructField(
                "metadata",
                types.MapType(
                    keyType=types.StringType(),
                    valueType=types.StructType(
                        [
                            types.StructField("value", types.StringType()),
                            types.StructField("type", types.StringType()),
                            types.StructField("timestamp", types.LongType()),
                            types.StructField("source", types.StringType()),
                        ]
                    ),
                ),
            ),
        ]
    )


@pytest.fixture()
def df_user(spark: SparkSession, user_row, user_schema):
    return spark.createDataFrame(data=[user_row], schema=user_schema)


def test_cli(spark: SparkSession, df_user, user_datacontract_no_desc):
    df_user.write.mode("overwrite").saveAsTable("users")

    expected_no_desc = user_datacontract_no_desc

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "import",
            "spark",
            "--tables",
            "users",
        ],
    )

    output = result.stdout
    assert result.exit_code == 0
    assert output.strip() == expected_no_desc.strip()


def test_table_not_exists():
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "import",
            "spark",
            "--tables",
            "table_not_exists",
        ],
    )

    assert result.exit_code == 1


def test_prog(spark: SparkSession, df_user, user_datacontract_no_desc, user_datacontract_desc):
    df_user.write.mode("overwrite").saveAsTable("users")

    expected_desc = user_datacontract_desc
    expected_no_desc = user_datacontract_no_desc

    # does not include a table level description (table method)
    result1 = DataContract.import_from_source("spark", "users")
    assert yaml.safe_load(result1.to_yaml()) == yaml.safe_load(expected_no_desc)

    # does include a table level description (table method)
    result2 = DataContract.import_from_source("spark", "users", description="description")
    assert yaml.safe_load(result2.to_yaml()) == yaml.safe_load(expected_desc)

    # does not include a table level description (dataframe object method)
    result3 = DataContract.import_from_source("spark", "users", dataframe=df_user)
    assert yaml.safe_load(result3.to_yaml()) == yaml.safe_load(expected_no_desc)

    # does include a table level description (dataframe object method)
    result4 = DataContract.import_from_source("spark", "users", dataframe=df_user, description="description")
    assert yaml.safe_load(result4.to_yaml()) == yaml.safe_load(expected_desc)


# Regression tests for issue #1048 — Spark importer physicalType must round-trip
# through the SQL type converters, not produce None ("has type None" silent passes).


def test_imported_spark_physical_types_map_to_databricks(df_user):
    """Every scalar / array / struct property of a Spark-imported contract must resolve
    to a real Databricks SQL type (not None → silent-pass). Map types are a pre-existing
    limitation (ODCS has no native map representation) and are out of scope for #1048."""
    contract = DataContract.import_from_source("spark", "users", dataframe=df_user)
    schema = contract.schema_[0]

    props_by_name = {p.name: p for p in schema.properties}
    assert convert_to_databricks(props_by_name["id"]) == "STRING"
    assert convert_to_databricks(props_by_name["name"]) == "STRING"
    assert convert_to_databricks(props_by_name["address"]).startswith("STRUCT<")
    assert convert_to_databricks(props_by_name["tags"]) == "ARRAY<STRING>"

    # Every non-map property must route to a real SQL type on both server kinds.
    for prop in schema.properties:
        if prop.name == "metadata":
            continue  # MapType: pre-existing ODCS limitation, tracked separately
        assert convert_to_databricks(prop) is not None, f"databricks mapping None for {prop.name}"
        assert convert_to_dataframe(prop) is not None, f"dataframe mapping None for {prop.name}"


def test_legacy_spark_repr_physical_types_still_map(caplog):
    """Contracts produced by v0.11.0–v0.12.1 (before #1048 fix) have Spark-repr physicalTypes
    like 'StringType()' / 'DecimalType(10,2)' / 'ArrayType(StringType(), True)'. The converters
    must recognise these as a compat shim so existing contracts still validate correctly."""
    items = SchemaProperty(name="items", physicalType="StringType()", logicalType="string")
    props = [
        SchemaProperty(name="s", physicalType="StringType()", logicalType="string"),
        SchemaProperty(name="i", physicalType="IntegerType()", logicalType="integer"),
        SchemaProperty(name="l", physicalType="LongType()", logicalType="integer"),
        SchemaProperty(name="b", physicalType="BooleanType()", logicalType="boolean"),
        SchemaProperty(name="d", physicalType="DateType()", logicalType="date"),
        SchemaProperty(name="ts", physicalType="TimestampType()", logicalType="date"),
        SchemaProperty(name="dec", physicalType="DecimalType(10,2)", logicalType="number"),
        SchemaProperty(name="a", physicalType="ArrayType(StringType(), True)", logicalType="array", items=items),
    ]
    expected = {
        "s": "STRING",
        "i": "INT",
        "l": "BIGINT",
        "b": "BOOLEAN",
        "d": "DATE",
        "ts": "TIMESTAMP",
        "dec": "DECIMAL(10,2)",
        "a": "ARRAY<STRING>",
    }
    with caplog.at_level(logging.WARNING, logger="datacontract.export.sql_type_converter"):
        for prop in props:
            assert convert_to_databricks(prop) == expected[prop.name], (
                f"{prop.name}: expected {expected[prop.name]!r}, got {convert_to_databricks(prop)!r}"
            )
    assert caplog.records == [], f"compat shim should not warn on legacy Spark-repr types: {caplog.records}"


def test_check_property_type_refuses_none_expected_type(caplog):
    """Defense in depth: SodaCL silently passes 'has type None' checks, so we must never
    build one. check_property_type should log a warning and return None for None input."""
    with caplog.at_level(logging.WARNING, logger="datacontract.engines.data_contract_checks"):
        result = check_property_type("model", "field", None)
    assert result is None
    assert any("None" in r.message and "field" in r.message for r in caplog.records)


def test_create_checks_skips_type_check_for_unmapped_physical_type(caplog):
    """When the SQL type converter can't map a physicalType, create_checks must NOT emit a
    type check (which would silently pass in SodaCL). It should log a warning instead."""
    contract = OpenDataContractStandard(
        version="1.0.0",
        kind="DataContract",
        apiVersion="v3.1.0",
        id="t",
        name="t",
    )
    schema = SchemaObject(name="m")
    # Use a non-parameterised unknown type: the `if _get_params(field): return _get_type(field)`
    # passthrough lets parameterised unknowns leak through by design (for custom SQL types).
    schema.properties = [SchemaProperty(name="f", physicalType="UnknownType", logicalType="string")]
    contract.schema_ = [schema]
    server = Server(server="s", type="databricks")
    with caplog.at_level(logging.WARNING, logger="datacontract.export.sql_type_converter"):
        checks = create_checks(contract, server)
    type_checks = [c for c in checks if c.type == "field_type"]
    assert type_checks == [], "Type check should be skipped for unmappable physicalType"
    assert any("UnknownType" in r.message for r in caplog.records)
