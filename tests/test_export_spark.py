from pyspark.sql import types
from pyspark.testing import assertSchemaEqual
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.export.spark_converter import to_spark_dict
from datacontract.model.data_contract_specification import DataContractSpecification

# logging.basicConfig(level=logging.DEBUG, force=True)


def test_cli():
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["export", "./fixtures/spark/export/datacontract.yaml", "--format", "spark"],
    )
    assert result.exit_code == 0
    assert result.output == expected_str


def test_to_spark_schema():
    data_contract = DataContractSpecification.from_file("fixtures/spark/export/datacontract.yaml")
    result = to_spark_dict(data_contract)

    assert len(result) == 2
    assertSchemaEqual(result.get("orders"), expected_dict.get("orders"))
    assertSchemaEqual(result.get("customers"), expected_dict.get("customers"))


expected_str = """orders = StructType([
    StructField("orderdate",
        DateType(),
        True
    ),
    StructField("order_timestamp",
        TimestampType(),
        True
    ),
    StructField("delivery_timestamp",
        TimestampNTZType(),
        True
    ),
    StructField("orderid",
        IntegerType(),
        True
    ),
    StructField("item_list",
        ArrayType(StructType([
            StructField("itemid",
                StringType(),
                True
            ),
            StructField("quantity",
                IntegerType(),
                True
            )
        ])),
        True
    ),
    StructField("orderunits",
        DoubleType(),
        True
    ),
    StructField("tags",
        ArrayType(StringType()),
        True
    ),
    StructField("address",
        StructType([
            StructField("city",
                StringType(),
                False
            ),
            StructField("state",
                StringType(),
                True
            ),
            StructField("zipcode",
                LongType(),
                True
            )
        ]),
        True
    )
])

customers = StructType([
    StructField("id",
        IntegerType(),
        True
    ),
    StructField("name",
        StringType(),
        True
    ),
    StructField("metadata",
        MapType(
            StringType(), StructType([
            StructField("value",
                StringType(),
                True
            ),
            StructField("type",
                StringType(),
                True
            ),
            StructField("timestamp",
                LongType(),
                True
            ),
            StructField("source",
                StringType(),
                True
            )
        ])),
        True
    )
])
"""

expected_dict = {
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
            types.StructField(
                "metadata",
                types.MapType(
                    types.StringType(),
                    types.StructType(
                        [
                            types.StructField("value", types.StringType()),
                            types.StructField("type", types.StringType()),
                            types.StructField("timestamp", types.LongType()),
                            types.StructField("source", types.StringType()),
                        ]
                    ),
                    True,
                ),
            ),
        ]
    ),
}
