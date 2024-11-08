import logging
import os

from datacontract.export.avro_converter import to_avro_schema_json
from datacontract.model.data_contract_specification import DataContractSpecification, Field, Server
from datacontract.model.exceptions import DataContractException


def create_spark_session(tmp_dir: str):
    """Create and configure a Spark session."""

    try:
        from pyspark.sql import SparkSession
    except ImportError as e:
        raise DataContractException(
            type="schema",
            result="failed",
            name="pyspark is missing",
            reason="Install the extra datacontract-cli[kafka] to use kafka",
            engine="datacontract",
            original_exception=e,
        )

    spark = (
        SparkSession.builder.appName("datacontract")
        .config("spark.sql.warehouse.dir", f"{tmp_dir}/spark-warehouse")
        .config("spark.streaming.stopGracefullyOnShutdown", "true")
        .config("spark.ui.enabled", "false")
        .config(
            "spark.jars.packages",
            "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.2,org.apache.spark:spark-avro_2.12:3.5.2",
        )
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")
    print(f"Using PySpark version {spark.version}")
    return spark


def read_kafka_topic(spark, data_contract: DataContractSpecification, server: Server, tmp_dir):
    """Read and process data from a Kafka topic based on the server configuration."""

    logging.info("Reading data from Kafka server %s topic %s", server.host, server.topic)
    df = (
        spark.read.format("kafka")
        .options(**get_auth_options())
        .option("kafka.bootstrap.servers", server.host)
        .option("subscribe", server.topic)
        .option("startingOffsets", "earliest")
        .load()
    )

    model_name, model = next(iter(data_contract.models.items()))

    match server.format:
        case "avro":
            process_avro_format(df, model_name, model)
        case "json":
            process_json_format(df, model_name, model)
        case _:
            raise DataContractException(
                type="test",
                name="Configuring Kafka checks",
                result="warning",
                reason=f"Kafka format '{server.format}' is not supported. " f"Skip executing tests.",
                engine="datacontract",
            )


def process_avro_format(df, model_name, model):
    try:
        from pyspark.sql.avro.functions import from_avro
        from pyspark.sql.functions import col, expr
    except ImportError as e:
        raise DataContractException(
            type="schema",
            result="failed",
            name="pyspark is missing",
            reason="Install the extra datacontract-cli[kafka] to use kafka",
            engine="datacontract",
            original_exception=e,
        )

    avro_schema = to_avro_schema_json(model_name, model)
    df2 = df.withColumn("fixedValue", expr("substring(value, 6, length(value)-5)"))
    options = {"mode": "PERMISSIVE"}
    df2.select(from_avro(col("fixedValue"), avro_schema, options).alias("avro")).select(
        col("avro.*")
    ).createOrReplaceTempView(model_name)


def process_json_format(df, model_name, model):
    try:
        from pyspark.sql.functions import col, from_json
    except ImportError as e:
        raise DataContractException(
            type="schema",
            result="failed",
            name="pyspark is missing",
            reason="Install the extra datacontract-cli[kafka] to use kafka",
            engine="datacontract",
            original_exception=e,
        )

    struct_type = to_struct_type(model.fields)
    df.selectExpr("CAST(key AS STRING)", "CAST(value AS STRING)").select(
        from_json(col("value"), struct_type, {"mode": "PERMISSIVE"}).alias("json")
    ).select(col("json.*")).createOrReplaceTempView(model_name)


def get_auth_options():
    """Retrieve Kafka authentication options from environment variables."""
    kafka_sasl_username = os.getenv("DATACONTRACT_KAFKA_SASL_USERNAME")
    kafka_sasl_password = os.getenv("DATACONTRACT_KAFKA_SASL_PASSWORD")
    kafka_sasl_mechanism = os.getenv("DATACONTRACT_KAFKA_SASL_MECHANISM", "PLAIN").upper()

    # Skip authentication if credentials are not provided
    if not kafka_sasl_username or not kafka_sasl_password:
        return {}

    # SASL mechanisms supported by Kafka
    jaas_config = {
        "PLAIN": (
            f"org.apache.kafka.common.security.plain.PlainLoginModule required "
            f'username="{kafka_sasl_username}" password="{kafka_sasl_password}";'
        ),
        "SCRAM-SHA-256": (
            f"org.apache.kafka.common.security.scram.ScramLoginModule required "
            f'username="{kafka_sasl_username}" password="{kafka_sasl_password}";'
        ),
        "SCRAM-SHA-512": (
            f"org.apache.kafka.common.security.scram.ScramLoginModule required "
            f'username="{kafka_sasl_username}" password="{kafka_sasl_password}";'
        ),
        # Add more mechanisms as needed
    }

    # Validate SASL mechanism
    if kafka_sasl_mechanism not in jaas_config:
        raise ValueError(f"Unsupported SASL mechanism: {kafka_sasl_mechanism}")

    # Return config
    return {
        "kafka.sasl.mechanism": kafka_sasl_mechanism,
        "kafka.security.protocol": "SASL_SSL",
        "kafka.sasl.jaas.config": jaas_config[kafka_sasl_mechanism],
    }


def to_struct_type(fields):
    try:
        from pyspark.sql.types import StructType
    except ImportError as e:
        raise DataContractException(
            type="schema",
            result="failed",
            name="pyspark is missing",
            reason="Install the extra datacontract-cli[kafka] to use kafka",
            engine="datacontract",
            original_exception=e,
        )

    """Convert field definitions to Spark StructType."""
    return StructType([to_struct_field(field_name, field) for field_name, field in fields.items()])


def to_struct_field(field_name: str, field: Field):
    try:
        from pyspark.sql.types import (
            ArrayType,
            BinaryType,
            BooleanType,
            DataType,
            DateType,
            DecimalType,
            DoubleType,
            IntegerType,
            LongType,
            NullType,
            StringType,
            StructField,
            StructType,
            TimestampNTZType,
            TimestampType,
        )
    except ImportError as e:
        raise DataContractException(
            type="schema",
            result="failed",
            name="pyspark is missing",
            reason="Install the extra datacontract-cli[kafka] to use kafka",
            engine="datacontract",
            original_exception=e,
        )

    """Map field definitions to Spark StructField using match-case."""
    match field.type:
        case "string" | "varchar" | "text":
            data_type = StringType()
        case "number" | "decimal" | "numeric":
            data_type = DecimalType()
        case "float" | "double":
            data_type = DoubleType()
        case "integer" | "int":
            data_type = IntegerType()
        case "long" | "bigint":
            data_type = LongType()
        case "boolean":
            data_type = BooleanType()
        case "timestamp" | "timestamp_tz":
            data_type = TimestampType()
        case "timestamp_ntz":
            data_type = TimestampNTZType()
        case "date":
            data_type = DateType()
        case "time":
            data_type = DataType()  # Specific handling for time type
        case "object" | "record" | "struct":
            data_type = StructType(
                [to_struct_field(sub_field_name, sub_field) for sub_field_name, sub_field in field.fields.items()]
            )
        case "binary":
            data_type = BinaryType()
        case "array":
            element_type = (
                StructType(
                    [to_struct_field(sub_field_name, sub_field) for sub_field_name, sub_field in field.fields.items()]
                )
                if field.fields
                else DataType()
            )
            data_type = ArrayType(element_type)
        case "null":
            data_type = NullType()
        case _:
            data_type = DataType()  # Fallback generic DataType

    return StructField(field_name, data_type, nullable=not field.required)
