from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col
from pyspark.sql.types import *

from datacontract.model.data_contract_specification import \
    DataContractSpecification, Server, Field


def create_spark_session():
    spark = (SparkSession.builder.appName("datacontract")
             .config("spark.streaming.stopGracefullyOnShutdown", True)
             .config('spark.jars.packages', 'org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0')
             .getOrCreate())
    print(f'Using PySpark version {spark.version}')
    return spark


def read_kafka_topic(spark, data_contract: DataContractSpecification, server: Server):
    host = server.host
    topic = server.topic
    df = spark \
        .readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", host) \
        .option("subscribe", topic) \
        .load()
    df2 = df.selectExpr("CAST(key AS STRING)", "CAST(value AS STRING)")
    schema = to_struct_type(data_contract)
    # TODO A good warning when the conversion to json fails
    df3 = df2.select(from_json(df2.value, schema).alias("json")).select(col("json.*"))
    model_name, model = next(iter(data_contract.models.items()))
    df3.createOrReplaceTempView(model_name)


def to_struct_type(data_contract: DataContractSpecification) -> StructType:
    model_name, model = next(iter(data_contract.models.items()))
    struct_fields = []
    for field_name, field in model.fields.items():
        struct_fields.append(to_struct_field(field_name, field))
    return StructType(struct_fields)


def to_struct_field(field_name: str, field: Field) -> StructField:
    if field.type == "string":
        data_type = StringType()
    elif field.type == "int":
        data_type = IntegerType()
    else:
        data_type = DataType()

    return StructField(field_name, data_type, nullable=not field.required)
