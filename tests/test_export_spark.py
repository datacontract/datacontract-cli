import logging

from typer.testing import CliRunner
from pyspark.sql import types
from pyspark.testing import assertSchemaEqual
from datacontract.cli import app
from datacontract.export.spark_converter import to_spark
from datacontract.model.data_contract_specification import DataContractSpecification

logging.basicConfig(level=logging.DEBUG, force=True)


def test_cli():
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["export", "./fixtures/spark/export/datacontract.yaml", "--format", "spark"],
    )
    assert result.exit_code == 0


def test_to_spark_schema():
    data_contract = DataContractSpecification.from_file("fixtures/spark/export/datacontract.yaml")
    result = to_spark(data_contract)

    assert len(result) == 2

    assertSchemaEqual(result.get("orders"), expected.get("orders"))
    assertSchemaEqual(result.get("customers"), expected.get("customers"))


expected = {
    "orders": types.StructType(
        [
            types.StructField("orderdate", types.DateType(), True),
            types.StructField("order_timestamp", types.TimestampType(), True),
            types.StructField("delivery_timestamp", types.TimestampNTZType(), True),
            types.StructField("orderid", types.IntegerType(), True),
            types.StructField(
                "item_list",
                types.ArrayType(
                    types.StructType(
                        [
                            types.StructField("itemid", types.StringType(), True),
                            types.StructField("quantity", types.IntegerType(), True),
                        ]
                    ),
                    True,
                ),
                True,
            ),
            types.StructField("orderunits", types.DoubleType(), True),
            types.StructField("tags", types.ArrayType(types.StringType(), True), True),
            types.StructField(
                "address",
                types.StructType(
                    [
                        types.StructField("city", types.StringType(), False),
                        types.StructField("state", types.StringType(), True),
                        types.StructField("zipcode", types.LongType(), True),
                    ]
                ),
                True,
            ),
        ]
    ),
    "customers": types.StructType(
        [
            types.StructField("id", types.IntegerType(), True),
            types.StructField("name", types.StringType(), True),
        ]
    ),
}
