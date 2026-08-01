import atexit
import logging
import os
import tempfile
from typing import List, Optional

from open_data_contract_standard.model import OpenDataContractStandard, SchemaObject, SchemaProperty, Server

from datacontract.config import getenv
from datacontract.export.avro_exporter import to_avro_schema_json
from datacontract.model.exceptions import DataContractException
from datacontract.model.run import ResultEnum


def _scala_binary_version() -> str:
    """Return the Scala binary version the installed PySpark was built against.

    The bundled ``spark-core_<scala>-<version>.jar`` is the source of truth; if
    it can't be located, fall back to the Spark major version (4.x ships Scala
    2.13, earlier lines ship 2.12).
    """
    import pyspark

    jars_dir = os.path.join(os.path.dirname(pyspark.__file__), "jars")
    try:
        for name in os.listdir(jars_dir):
            if name.startswith("spark-core_") and name.endswith(".jar"):
                # spark-core_<scala>-<version>.jar
                return name[len("spark-core_") :].split("-", 1)[0]
    except OSError:
        pass
    major = int(pyspark.__version__.split(".", 1)[0])
    return "2.13" if major >= 4 else "2.12"


def spark_connector_packages() -> str:
    """Maven coordinates for the Kafka and Avro Spark connectors.

    Derived from the installed PySpark runtime so the fetched JARs always match
    the running Spark version and its Scala binary version. Resolving these
    against a mismatched runtime (e.g. 3.5 JARs on a Spark 4 / Scala 2.13
    runtime) fails at session startup.
    """
    import pyspark

    spark_version = pyspark.__version__
    scala_version = _scala_binary_version()
    return (
        f"org.apache.spark:spark-sql-kafka-0-10_{scala_version}:{spark_version},"
        f"org.apache.spark:spark-avro_{scala_version}:{spark_version}"
    )


def create_spark_session():
    """Create and configure a Spark session."""

    try:
        from pyspark.sql import SparkSession
    except ImportError as e:
        raise DataContractException(
            type="schema",
            result=ResultEnum.failed,
            name="pyspark is missing",
            reason="Install the extra datacontract-cli[kafka] to use kafka",
            engine="datacontract",
            original_exception=e,
        )

    tmp_dir = tempfile.TemporaryDirectory(prefix="datacontract-cli-spark")
    atexit.register(tmp_dir.cleanup)

    # Make Spark's Python workers use the same interpreter as the driver. Without
    # this, PySpark launches workers from the `python3` on PATH, which fails with
    # PYTHON_VERSION_MISMATCH when it differs from the running interpreter (common
    # on Python 3.13, where Spark 3.5 isn't available and Spark 4.x is used).
    import sys

    os.environ.setdefault("PYSPARK_PYTHON", sys.executable)
    os.environ.setdefault("PYSPARK_DRIVER_PYTHON", sys.executable)

    spark = (
        SparkSession.builder.appName("datacontract")
        .config("spark.sql.warehouse.dir", f"{tmp_dir.name}/spark-warehouse")
        .config("spark.streaming.stopGracefullyOnShutdown", "true")
        .config("spark.ui.enabled", "false")
        .config("spark.driver.bindAddress", "127.0.0.1")
        .config("spark.driver.host", "127.0.0.1")
        .config("spark.jars.packages", spark_connector_packages())
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")
    print(f"Using PySpark version {spark.version}")
    return spark


def read_kafka_topic(spark, data_contract: OpenDataContractStandard, server: Server):
    """Read and process data from a Kafka topic based on the server configuration."""

    if not data_contract.schema_ or len(data_contract.schema_) == 0:
        raise DataContractException(
            type="test",
            name="Configuring Kafka checks",
            result="warning",
            reason="No schema defined in data contract. Skip executing tests.",
            engine="datacontract",
        )

    schema_obj = data_contract.schema_[0]
    model_name = schema_obj.name
    topic = schema_obj.physicalName or schema_obj.name

    logging.info("Reading data from Kafka server %s topic %s", server.host, topic)
    df = (
        spark.read.format("kafka")
        .options(**get_auth_options())
        .option("kafka.bootstrap.servers", server.host)
        .option("subscribe", topic)
        .option("startingOffsets", "earliest")
        .load()
    )

    match server.format:
        case "avro":
            process_avro_format(df, model_name, schema_obj)
        case "json":
            process_json_format(df, model_name, schema_obj)
        case _:
            raise DataContractException(
                type="test",
                name="Configuring Kafka checks",
                result="warning",
                reason=f"Kafka format '{server.format}' is not supported. Skip executing tests.",
                engine="datacontract",
            )


# Messages serialized through the Confluent Schema Registry are framed with a 5-byte
# prefix: magic byte 0x00 followed by the 4-byte big-endian id of the schema they were
# written with. Plain Avro messages carry no such prefix.
_IS_CONFLUENT_FRAMED = "substring(value, 1, 1) = X'00'"


def process_avro_format(df, model_name: str, schema_obj: SchemaObject):
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

    contract_schema = to_avro_schema_json(model_name, schema_obj)
    # Strip the Confluent prefix only when the magic byte is present; otherwise
    # stripping 5 bytes would corrupt every plain Avro record (#1344).
    framed = df.withColumn(
        "fixedValue",
        expr(f"CASE WHEN {_IS_CONFLUENT_FRAMED} THEN substring(value, 6, length(value)-5) ELSE value END"),
    ).withColumn(
        "schemaId",
        expr(f"CASE WHEN {_IS_CONFLUENT_FRAMED} THEN conv(hex(substring(value, 2, 4)), 16, 10) END").cast("long"),
    )

    registry = get_schema_registry_config()
    decoded = None
    for schema_id, part in _partition_by_writer_schema(framed, registry):
        if schema_id is None:
            source, avro_schema = "the data contract", contract_schema
        else:
            source = f"schema id {schema_id} in the schema registry at {registry['url']}"
            avro_schema = fetch_writer_schema(registry, schema_id)
        # Avro is positionally encoded, so from_avro must be given the schema the
        # messages were *written* with, not one that merely looks like it. FAILFAST
        # surfaces a mismatch as an error; PERMISSIVE would decode every message to a
        # record with all fields null, which then shows up as missing values on data
        # that is not null at all (#1347).
        rows = part.select(from_avro(col("fixedValue"), avro_schema, {"mode": "FAILFAST"}).alias("avro"))
        _check_messages_are_decodable(rows, source, registry is not None)
        flat = rows.select(col("avro.*"))
        decoded = flat if decoded is None else decoded.unionByName(flat, allowMissingColumns=True)

    decoded.createOrReplaceTempView(model_name)


def _partition_by_writer_schema(framed, registry: Optional[dict]) -> list:
    """Split the messages into groups that share one Avro writer schema.

    Without a schema registry there is only one candidate schema — the one derived from
    the data contract — so everything stays in a single group (schema id ``None``). With
    a registry, each distinct schema id in the Confluent prefix forms its own group, so a
    topic whose schema evolved still decodes.
    """
    from pyspark.sql.functions import col

    if registry is None:
        return [(None, framed)]

    schema_ids = [row[0] for row in framed.select("schemaId").distinct().collect()]
    schema_ids.sort(key=lambda schema_id: (schema_id is None, schema_id))
    if not schema_ids:  # empty topic
        return [(None, framed)]
    return [
        (schema_id, framed.filter(col("schemaId").isNull() if schema_id is None else col("schemaId") == schema_id))
        for schema_id in schema_ids
    ]


def _check_messages_are_decodable(rows, source: str, registry_configured: bool):
    """Decode the messages eagerly so a schema mismatch is reported as a schema mismatch."""
    try:
        rows.write.format("noop").mode("overwrite").save()
    except Exception as e:
        hint = (
            ""
            if registry_configured
            else (
                " If the topic is written through the Confluent Schema Registry, set "
                "DATACONTRACT_KAFKA_SCHEMA_REGISTRY_URL so that the schema the messages were written "
                "with is read from the registry instead of being derived from the data contract."
            )
        )
        raise DataContractException(
            type="test",
            name="Configuring Kafka checks",
            result=ResultEnum.failed,
            reason=(
                f"Cannot decode the Avro messages of the topic with the schema from {source}. "
                f"Avro is positionally encoded, so it must be the exact schema the messages "
                f"were written with.{hint}"
            ),
            engine="datacontract",
            original_exception=e,
        )


def get_schema_registry_config() -> Optional[dict]:
    """Confluent Schema Registry settings from the environment, or None if not configured."""
    url = getenv("DATACONTRACT_KAFKA_SCHEMA_REGISTRY_URL")
    if not url:
        return None
    return {
        "url": url.rstrip("/"),
        "username": getenv("DATACONTRACT_KAFKA_SCHEMA_REGISTRY_USERNAME"),
        "password": getenv("DATACONTRACT_KAFKA_SCHEMA_REGISTRY_PASSWORD"),
    }


def fetch_writer_schema(registry: dict, schema_id: int) -> str:
    """Fetch the Avro schema the Confluent-framed messages with this schema id were written with."""
    import requests

    url = f"{registry['url']}/schemas/ids/{schema_id}"
    auth = (registry["username"], registry["password"]) if registry["username"] else None
    try:
        response = requests.get(url, auth=auth, timeout=30)
        response.raise_for_status()
        body = response.json()
    except (requests.RequestException, ValueError) as e:
        raise DataContractException(
            type="test",
            name="Configuring Kafka checks",
            result=ResultEnum.failed,
            reason=f"Cannot fetch Avro schema id {schema_id} from the schema registry at {registry['url']}: {e}",
            engine="datacontract",
            original_exception=e,
        )
    schema_type = body.get("schemaType", "AVRO")
    if schema_type != "AVRO":
        raise DataContractException(
            type="test",
            name="Configuring Kafka checks",
            result=ResultEnum.failed,
            reason=(
                f"Schema id {schema_id} in the schema registry at {registry['url']} is a {schema_type} schema, "
                f"but the server format is avro."
            ),
            engine="datacontract",
        )
    return body["schema"]


def process_json_format(df, model_name: str, schema_obj: SchemaObject):
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

    struct_type = to_struct_type(schema_obj.properties or [])
    df.selectExpr("CAST(key AS STRING)", "CAST(value AS STRING)").select(
        from_json(col("value"), struct_type, {"mode": "PERMISSIVE"}).alias("json")
    ).select(col("json.*")).createOrReplaceTempView(model_name)


def get_auth_options():
    """Retrieve Kafka authentication options from environment variables."""
    kafka_sasl_username = getenv("DATACONTRACT_KAFKA_SASL_USERNAME")
    kafka_sasl_password = getenv("DATACONTRACT_KAFKA_SASL_PASSWORD")
    kafka_sasl_mechanism = getenv("DATACONTRACT_KAFKA_SASL_MECHANISM", "PLAIN").upper()

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


def _get_type(prop: SchemaProperty) -> Optional[str]:
    """Get the type from a schema property. Prefers physicalType for accurate type checking."""
    if prop.physicalType:
        return prop.physicalType
    if prop.logicalType:
        return prop.logicalType
    return None


def to_struct_type(properties: List[SchemaProperty]):
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
    return StructType([to_struct_field(prop.name, prop) for prop in properties])


def to_struct_field(field_name: str, prop: SchemaProperty):
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
    field_type = _get_type(prop)
    match field_type:
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
            nested_props = prop.properties or []
            data_type = StructType([to_struct_field(p.name, p) for p in nested_props])
        case "binary":
            data_type = BinaryType()
        case "array":
            if prop.items and prop.items.properties:
                element_type = StructType([to_struct_field(p.name, p) for p in prop.items.properties])
            else:
                element_type = DataType()
            data_type = ArrayType(element_type)
        case "null":
            data_type = NullType()
        case _:
            data_type = DataType()  # Fallback generic DataType

    return StructField(field_name, data_type, nullable=not prop.required)
