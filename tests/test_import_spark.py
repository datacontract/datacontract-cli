import yaml
import pytest
from pyspark.sql import types

from pyspark.sql import SparkSession

from datacontract.data_contract import DataContract

from typer.testing import CliRunner
from datacontract.cli import app


expected = """
dataContractSpecification: 0.9.3
id: my-data-contract-id
info:
  title: My Data Contract
  version: 0.0.1
servers:
  local:
    type: dataframe
models:
  users:
    fields:
      id:
        type: string
        required: false
      name:
        type: string
        required: false
      address:
        type: struct
        required: false
        fields:
          number:
            type: integer
            required: false
          street:
            type: string
            required: false
          city:
            type: string
            required: false
      tags:
        type: array
        required: false
        items:
          type: string
          required: false
      metadata:
        type: map
        required: false
        keys:
          type: string
          required: true
        values:
          type: struct
          required: false
          fields:
            value:
              type: string
              required: false
            type:
              type: string
              required: false
            timestamp:
              type: long
              required: false
            source:
              type: string
              required: false
    """


@pytest.fixture(scope="session")
def spark(tmp_path_factory) -> SparkSession:
    """Create and configure a Spark session."""
    spark = (
        SparkSession.builder.appName("datacontract-dataframe-unittest")
        .config(
            "spark.sql.warehouse.dir",
            f"{tmp_path_factory.mktemp('spark')}/spark-warehouse",
        )
        .config("spark.streaming.stopGracefullyOnShutdown", "true")
        .config(
            "spark.jars.packages",
            "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0,org.apache.spark:spark-avro_2.12:3.5.0",
        )
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")
    print(f"Using PySpark version {spark.version}")
    return spark


def test_cli(spark: SparkSession):
    df_user = spark.createDataFrame(
        data=[
            {
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
        ],
        schema=types.StructType(
            [
                types.StructField("id", types.StringType()),
                types.StructField("name", types.StringType()),
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
        ),
    )

    df_user.createOrReplaceTempView("users")
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "import",
            "--format",
            "spark",
            "--source",
            "users",
        ],
    )

    output = result.stdout
    assert result.exit_code == 0
    assert output.strip() == expected.strip()


def test_table_not_exists():
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "import",
            "--format",
            "spark",
            "--source",
            "table_not_exists",
        ],
    )

    assert result.exit_code == 1


def test_prog(spark: SparkSession):
    df_user = spark.createDataFrame(
        data=[
            {
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
        ],
        schema=types.StructType(
            [
                types.StructField("id", types.StringType()),
                types.StructField("name", types.StringType()),
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
        ),
    )

    df_user.createOrReplaceTempView("users")
    result = DataContract().import_from_source("spark", "users")

    assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected)
