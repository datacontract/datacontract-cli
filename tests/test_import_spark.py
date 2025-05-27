import pytest
import yaml
from pyspark.sql import SparkSession, types
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract


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
            "--format",
            "spark",
            "--source",
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
            "--format",
            "spark",
            "--source",
            "table_not_exists",
        ],
    )

    assert result.exit_code == 1


def test_prog(spark: SparkSession, df_user, user_datacontract_no_desc, user_datacontract_desc):

    df_user.write.mode("overwrite").saveAsTable("users")

    expected_desc = user_datacontract_desc
    expected_no_desc = user_datacontract_no_desc    
    
    # does not include a table level description (table method)
    result1 = DataContract().import_from_source("spark", "users")
    assert yaml.safe_load(result1.to_yaml()) == yaml.safe_load(expected_no_desc)

    # does include a table level description (table method)
    result2 = DataContract().import_from_source("spark", "users", description = "description")
    assert yaml.safe_load(result2.to_yaml()) == yaml.safe_load(expected_desc)

    # does not include a table level description (dataframe object method)
    result3 = DataContract().import_from_source("spark", "users", dataframe = df_user)
    assert yaml.safe_load(result3.to_yaml()) == yaml.safe_load(expected_no_desc)
    
    # does include a table level description (dataframe object method)
    result4 = DataContract().import_from_source("spark", "users", dataframe = df_user, description = "description")
    assert yaml.safe_load(result4.to_yaml()) == yaml.safe_load(expected_desc)