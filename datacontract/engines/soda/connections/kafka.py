import os

import pyspark.sql.functions as fn
from pyspark.sql import SparkSession
from pyspark.sql.avro.functions import from_avro
from pyspark.sql.functions import from_json, col
from pyspark.sql.types import *

from datacontract.export.avro_converter import to_avro_schema_json
from datacontract.model.data_contract_specification import \
    DataContractSpecification, Server, Field
from datacontract.model.exceptions import DataContractException


def create_spark_session(tmp_dir) -> SparkSession:
    # TODO: Update dependency versions when updating pyspark
    # TODO: add protobuf library
    spark = SparkSession.builder.appName("datacontract") \
        .config("spark.sql.warehouse.dir", tmp_dir + "/spark-warehouse") \
        .config("spark.streaming.stopGracefullyOnShutdown", True) \
        .config('spark.jars.packages',
                'org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0,org.apache.spark:spark-avro_2.12:3.5.0') \
        .getOrCreate()
    spark.sparkContext.setLogLevel("WARN")
    print(f'Using PySpark version {spark.version}')
    return spark


def read_kafka_topic(spark: SparkSession, data_contract: DataContractSpecification, server: Server, tmp_dir):
    host = server.host
    topic = server.topic
    auth_options = get_auth_options()

    # read full kafka topic
    df = spark \
        .read \
        .format("kafka") \
        .options(**auth_options) \
        .option("kafka.bootstrap.servers", host) \
        .option("subscribe", topic) \
        .option("startingOffsets", "earliest") \
        .load()
    # TODO a warning if none or multiple models
    model_name, model = next(iter(data_contract.models.items()))
    if server.format == "avro":
        avro_schema = to_avro_schema_json(model_name, model)

        # Parse out the extra bytes from the Avro data
        # A Kafka message contains a key and a value. Data going through a Kafka topic in Confluent Cloud has five bytes added to the beginning of every Avro value. If you are using Avro format keys, then five bytes will be added to the beginning of those as well. For this example, we’re assuming string keys. These bytes consist of one magic byte and four bytes representing the schema ID of the schema in the registry that is needed to decode that data. The bytes need to be removed so that the schema ID can be determined and the Avro data can be parsed. To manipulate the data, we need a couple of imports:
        df2 = df.withColumn("fixedValue", fn.expr("substring(value, 6, length(value)-5)"))

        options = {"mode": "PERMISSIVE"}
        df3 = df2.select(from_avro(col("fixedValue"), avro_schema, options).alias("avro")).select(col("avro.*"))
    elif server.format == "json":
        # TODO A good warning when the conversion to json fails
        struct_type = to_struct_type(model.fields)
        df2 = df.selectExpr("CAST(key AS STRING)", "CAST(value AS STRING)")

        options = {"mode": "PERMISSIVE"}
        df3 = df2.select(from_json(df2.value, struct_type, options).alias("json")).select(col("json.*"))
    else:
        raise DataContractException(
            type="test",
            name="Configuring Kafka checks",
            result="warning",
            reason=f"Kafka format '{server.format}' is not supported. Skip executing tests.",
            engine="datacontract",
        )

    # df3.writeStream.toTable(model_name, checkpointLocation=tmp_dir + "/checkpoint")
    df3.createOrReplaceTempView(model_name)
    # print(spark.sql(f"select * from {model_name}").show())


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

