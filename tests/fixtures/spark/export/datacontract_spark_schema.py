from pyspark.sql import types

spark_schema = {
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
