import os

from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col
from pyspark.sql.types import *

from datacontract.model.data_contract_specification import \
    DataContractSpecification, Server, Field


def create_spark_session(tmp_dir) -> SparkSession:
    spark = SparkSession.builder.appName("datacontract") \
        .config("spark.sql.warehouse.dir", tmp_dir + "/spark-warehouse") \
        .config("spark.streaming.stopGracefullyOnShutdown", True) \
        .config('spark.jars.packages', 'org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0') \
        .getOrCreate()
    spark.sparkContext.setLogLevel("WARN")
    print(f'Using PySpark version {spark.version}')
    return spark


def read_kafka_topic(spark: SparkSession, data_contract: DataContractSpecification, server: Server, tmp_dir):
    host = server.host
    topic = server.topic
    auth_options = get_auth_options()

    df = spark \
        .read \
        .format("kafka") \
        .options(**auth_options) \
        .option("kafka.bootstrap.servers", host) \
        .option("subscribe", topic) \
        .option("startingOffsets", "earliest") \
        .load()
    df2 = df.selectExpr("CAST(key AS STRING)", "CAST(value AS STRING)")
    name, model1 = next(iter(data_contract.models.items()))
    schema = to_struct_type(model1.fields)
    # TODO A good warning when the conversion to json fails
    df3 = df2.select(from_json(df2.value, schema).alias("json")).select(col("json.*"))
    model_name, model = next(iter(data_contract.models.items()))
    # df3.writeStream.toTable(model_name, checkpointLocation=tmp_dir + "/checkpoint")
    df3.createOrReplaceTempView(model_name)

    print(spark.sql(f"select * from {model_name}").show())


def get_auth_options():
    kafka_sasl_username = os.getenv('DATACONTRACT_KAFKA_SASL_USERNAME')
    kafka_sasl_password = os.getenv('DATACONTRACT_KAFKA_SASL_PASSWORD')
    if kafka_sasl_username is None:
        auth_options = {}
    else:
        kafka_sasl_jaas_config = f'org.apache.kafka.common.security.plain.PlainLoginModule required username="{kafka_sasl_username}" password="{kafka_sasl_password}";'
        auth_options = {
            "kafka.sasl.mechanism": "PLAIN",
            "kafka.security.protocol": "SASL_SSL",
            "kafka.sasl.jaas.config": kafka_sasl_jaas_config,
        }
    return auth_options


def to_struct_type(fields):
    struct_fields = []
    for field_name, field in fields.items():
        struct_fields.append(to_struct_field(field_name, field))
    return StructType(struct_fields)


def to_struct_field(field_name: str, field: Field) -> StructField:
    if field.type is None:
        data_type = DataType()
    if field.type in ["string", "varchar", "text"]:
        data_type = StringType()
    elif field.type in ["number", "decimal", "numeric"]:
        data_type = DecimalType()
    elif field.type in ["float", "double"]:
        data_type = DoubleType()
    elif field.type in ["integer", "int"]:
        data_type = IntegerType()
    elif field.type in ["long", "bigint"]:
        data_type = LongType()
    elif field.type in ["boolean"]:
        data_type = BooleanType()
    elif field.type in ["timestamp", "timestamp_tz"]:
        data_type = TimestampType()
    elif field.type in ["timestamp_ntz"]:
        data_type = TimestampNTZType()
    elif field.type in ["date"]:
        data_type = DateType()
    elif field.type in ["time"]:
        data_type = DataType()
    elif field.type in ["object", "record", "struct"]:
        data_type = to_struct_type(field.fields)
    elif field.type in ["binary"]:
        data_type = BinaryType()
    elif field.type in ["array"]:
        # TODO support array structs
        data_type = ArrayType()
    elif field.type in ["null"]:
        data_type = NullType()
    else:
        data_type = DataType()

    return StructField(field_name, data_type, nullable=not field.required)
