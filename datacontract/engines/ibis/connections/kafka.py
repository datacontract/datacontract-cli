"""Read a Kafka topic into an in-memory DuckDB database.

The topic is consumed with confluent-kafka, every message is decoded in Python
(fastavro for Avro, the standard library for JSON), and the records are
registered as a DuckDB table named after the contract's schema object. From
there the ibis check engine queries it like any other DuckDB source.

This used to run on Spark: the ``spark-sql-kafka-0-10`` connector did the
consuming, ``from_avro`` / ``from_json`` the decoding, and the checks ran
through ``ibis.pyspark`` against a temp view. Nothing about that needed a
cluster — a CLI run is single-process either way — while pyspark pulled ~320
JARs and a JDK into every install. The Python stack does the same work with
wheels only, and no Java.

Two behaviours differ from the Spark implementation, both deliberate:

- Avro unions of more than one non-null type are rejected with an explicit
  error instead of being decoded into a struct of members.
- Messages with a null value (compaction tombstones) are skipped rather than
  decoded into a row of nulls.
"""

from __future__ import annotations

import io
import json
import logging
import time
import uuid
from typing import Any, List, Optional, Tuple

from open_data_contract_standard.model import OpenDataContractStandard, SchemaObject, SchemaProperty, Server

from datacontract.config import Config
from datacontract.export.avro_exporter import to_avro_schema_json
from datacontract.model.exceptions import DataContractException
from datacontract.model.run import ResultEnum, Run

logger = logging.getLogger(__name__)

# Messages serialized through the Confluent Schema Registry are framed with a 5-byte
# prefix: magic byte 0x00 followed by the 4-byte big-endian id of the schema they were
# written with. Plain Avro messages carry no such prefix.
_CONFLUENT_MAGIC_BYTE = 0x00
_CONFLUENT_PREFIX_LENGTH = 5

# Consuming stops once every partition reports EOF, so this only bounds the wait
# for a broker that accepts the connection but never answers. It is an *idle*
# timeout: it resets on every message, so a slow but progressing read is never cut off.
_DEFAULT_TIMEOUT_SECONDS = 30

# Timeout for the metadata and watermark-offset lookups that precede the read.
_METADATA_TIMEOUT_SECONDS = 30

_SASL_MECHANISMS = ("PLAIN", "SCRAM-SHA-256", "SCRAM-SHA-512")


def _import(module: str):
    try:
        return __import__(module, fromlist=["_"])
    except ImportError as e:
        raise DataContractException(
            type="schema",
            result=ResultEnum.failed,
            name=f"{module} is missing",
            reason="Install the extra datacontract-cli[kafka] to use kafka",
            engine="datacontract-cli",
            original_exception=e,
        )


def read_kafka_topic(
    data_contract: OpenDataContractStandard,
    server: Server,
    run: Run | None = None,
    config: Config | None = None,
    duckdb_connection=None,
):
    """Consume a Kafka topic and return a DuckDB connection holding its messages."""
    config = Config.resolve(config)

    if not data_contract.schema_ or len(data_contract.schema_) == 0:
        raise DataContractException(
            type="test",
            name="Configuring Kafka checks",
            result="warning",
            reason="No schema defined in data contract. Skip executing tests.",
            engine="datacontract-cli",
        )

    schema_obj = data_contract.schema_[0]
    model_name = schema_obj.name
    topic = schema_obj.physicalName or schema_obj.name

    if server.format not in ("avro", "json"):
        raise DataContractException(
            type="test",
            name="Configuring Kafka checks",
            result="warning",
            reason=f"Kafka format '{server.format}' is not supported. Skip executing tests.",
            engine="datacontract-cli",
        )

    logger.info("Reading data from Kafka server %s topic %s", server.host, topic)
    values = consume_topic(topic, server, run, config)

    if server.format == "avro":
        table = _decode_avro(values, model_name, schema_obj, config)
    else:
        table = _decode_json(values, schema_obj)

    duckdb = _import("duckdb")
    con = duckdb_connection if duckdb_connection is not None else duckdb.connect(database=":memory:")
    con.register("_datacontract_kafka_messages", table)
    try:
        con.sql(
            f"CREATE OR REPLACE TABLE {_quoted(model_name)} AS SELECT * FROM _datacontract_kafka_messages"  # noqa: S608
        )
    finally:
        con.unregister("_datacontract_kafka_messages")
    if run is not None:
        run.log_info(f"Read {table.num_rows} messages from topic {topic} into table {model_name}")
    return con


def _quoted(identifier: str) -> str:
    """Quote a duckdb identifier, escaping any embedded double quote."""
    return '"{}"'.format(identifier.replace('"', '""'))


# ---------------------------------------------------------------------------
# consuming
# ---------------------------------------------------------------------------
def consume_topic(topic: str, server: Server, run: Run | None, config: Config | None = None) -> List[bytes]:
    """Read a topic from its earliest to its current latest offset.

    Equivalent to the batch read Spark did with ``startingOffsets=earliest``:
    the end offsets are resolved once up front, so messages produced while the
    read is running are not part of the result.
    """
    config = Config.resolve(config)
    confluent_kafka = _import("confluent_kafka")
    from confluent_kafka import KafkaError, KafkaException, TopicPartition

    max_messages = config.get_kafka_max_messages()
    idle_timeout = config.get_kafka_timeout() or _DEFAULT_TIMEOUT_SECONDS

    consumer = confluent_kafka.Consumer(_consumer_config(server, config))
    try:
        assignments, expected = _resolve_offsets(consumer, topic, server, TopicPartition)
        if not assignments:
            return []
        consumer.assign(assignments)

        limit = min(expected, max_messages) if max_messages else expected
        values: List[bytes] = []
        finished: set = set()
        skipped_tombstones = 0
        deadline = time.monotonic() + idle_timeout

        while len(values) < limit and len(finished) < len(assignments):
            message = consumer.poll(1.0)
            if message is None:
                if time.monotonic() > deadline:
                    break
                continue
            deadline = time.monotonic() + idle_timeout
            error = message.error()
            if error is not None:
                if error.code() == KafkaError._PARTITION_EOF:
                    finished.add(message.partition())
                    continue
                raise KafkaException(error)
            if message.value() is None:
                # A compaction tombstone carries no payload to check.
                skipped_tombstones += 1
                continue
            values.append(message.value())

        if run is not None:
            if skipped_tombstones:
                run.log_info(f"Skipped {skipped_tombstones} messages without a value (tombstones)")
            if max_messages and len(values) >= max_messages and max_messages < expected:
                run.log_warn(
                    f"Only the first {len(values)} of {expected} messages in topic {topic} were read, "
                    f"as limited by DATACONTRACT_KAFKA_MAX_MESSAGES. The checks describe that sample, "
                    f"not the whole topic."
                )
        return values
    finally:
        consumer.close()


def _resolve_offsets(consumer, topic: str, server: Server, TopicPartition) -> Tuple[list, int]:
    """Assign every partition of the topic at its earliest offset.

    Returns the assignments and how many messages they span, so the read can
    stop once the topic has been consumed rather than idling on an open poll.
    """
    metadata = consumer.list_topics(topic, timeout=_METADATA_TIMEOUT_SECONDS)
    topic_metadata = metadata.topics.get(topic)
    if topic_metadata is None or topic_metadata.error is not None:
        reason = topic_metadata.error if topic_metadata is not None else "topic not found"
        raise DataContractException(
            type="test",
            name="Configuring Kafka checks",
            result=ResultEnum.failed,
            reason=f"Cannot read topic {topic} from the Kafka server {server.host}: {reason}",
            engine="datacontract-cli",
        )

    assignments, expected = [], 0
    for partition in sorted(topic_metadata.partitions):
        low, high = consumer.get_watermark_offsets(
            TopicPartition(topic, partition), timeout=_METADATA_TIMEOUT_SECONDS, cached=False
        )
        if high > low:
            assignments.append(TopicPartition(topic, partition, low))
            expected += high - low
    return assignments, expected


def _consumer_config(server: Server, config: Config) -> dict:
    """librdkafka settings for a one-off, read-only, non-committing consumer."""
    prefix = config.get_kafka_group_prefix() or "datacontract-cli-"
    settings = {
        "bootstrap.servers": server.host,
        # A fresh group id per run, with commits off, so a test run never
        # interferes with the offsets of a real consumer group.
        "group.id": f"{prefix}{uuid.uuid4()}",
        "enable.auto.commit": False,
        "auto.offset.reset": "earliest",
        # Report end-of-partition so the read knows when the topic is exhausted.
        "enable.partition.eof": True,
    }
    settings.update(get_auth_options(config))
    return settings


def get_auth_options(config: Config | None = None) -> dict:
    """Retrieve Kafka authentication options from the config or environment variables."""
    config = Config.resolve(config)
    kafka_sasl_username = config.get_kafka_sasl_username()
    kafka_sasl_password = config.get_kafka_sasl_password()
    kafka_sasl_mechanism = (config.get_kafka_sasl_mechanism() or "PLAIN").upper()

    # Skip authentication if credentials are not provided
    if not kafka_sasl_username or not kafka_sasl_password:
        return {}

    if kafka_sasl_mechanism not in _SASL_MECHANISMS:
        raise ValueError(f"Unsupported SASL mechanism: {kafka_sasl_mechanism}")

    return {
        "security.protocol": "SASL_SSL",
        "sasl.mechanism": kafka_sasl_mechanism,
        "sasl.username": kafka_sasl_username,
        "sasl.password": kafka_sasl_password,
    }


# ---------------------------------------------------------------------------
# avro
# ---------------------------------------------------------------------------
def _decode_avro(values: List[bytes], model_name: str, schema_obj: SchemaObject, config: Config | None = None):
    """Decode Avro messages, each with the schema it was written with."""
    pa = _import("pyarrow")
    fastavro = _import("fastavro")

    contract_schema = json.loads(to_avro_schema_json(model_name, schema_obj))
    registry = get_schema_registry_config(config)

    tables = []
    for schema_id, payloads in _group_by_writer_schema(values, registry):
        if schema_id is None:
            source, avro_schema = "the data contract", contract_schema
        else:
            source = f"schema id {schema_id} in the schema registry at {registry['url']}"
            avro_schema = json.loads(fetch_writer_schema(registry, schema_id))

        parsed = fastavro.parse_schema(avro_schema)
        records = []
        for payload in payloads:
            # Avro is positionally encoded, so the messages must be read with the schema
            # they were *written* with, not one that merely looks like it. Decoding with
            # the wrong schema either raises or yields records of nulls, which shows up as
            # missing values on data that is not null at all (#1347).
            try:
                records.append(fastavro.schemaless_reader(io.BytesIO(payload), parsed))
            except Exception as e:
                raise _undecodable(source, registry is not None, e)
        tables.append(_records_to_arrow(pa, records, _avro_schema_to_arrow(pa, avro_schema)))

    if not tables:
        return _records_to_arrow(pa, [], _avro_schema_to_arrow(pa, contract_schema))
    # A topic whose schema evolved decodes into one table per writer schema;
    # `permissive` unions them by name, filling in the columns a table lacks.
    return pa.concat_tables(tables, promote_options="permissive")


def _group_by_writer_schema(values: List[bytes], registry: Optional[dict]) -> List[Tuple[Optional[int], List[bytes]]]:
    """Split the messages into groups that share one Avro writer schema.

    Confluent-framed messages are grouped by the schema id in their prefix, with
    the prefix stripped; unframed messages form the ``None`` group and are read
    with the schema derived from the data contract. Stripping the 5 bytes only
    where the magic byte is present keeps plain Avro records intact (#1344).
    """
    groups: dict[Optional[int], List[bytes]] = {}
    for value in values:
        if len(value) > _CONFLUENT_PREFIX_LENGTH and value[0] == _CONFLUENT_MAGIC_BYTE:
            schema_id = int.from_bytes(value[1:_CONFLUENT_PREFIX_LENGTH], "big")
            payload = value[_CONFLUENT_PREFIX_LENGTH:]
        else:
            schema_id, payload = None, value
        groups.setdefault(schema_id, []).append(payload)

    if registry is None and any(schema_id is not None for schema_id in groups):
        raise DataContractException(
            type="test",
            name="Configuring Kafka checks",
            result=ResultEnum.failed,
            reason=(
                "Cannot decode the Avro messages of the topic: they are framed with a Confluent "
                "Schema Registry schema id, so the schema they were written with is held in the "
                "registry rather than derivable from the data contract. Set "
                "DATACONTRACT_KAFKA_SCHEMA_REGISTRY_URL so it can be read from there."
            ),
            engine="datacontract-cli",
        )

    return sorted(groups.items(), key=lambda item: (item[0] is not None, item[0]))


def _undecodable(source: str, registry_configured: bool, cause: Exception) -> DataContractException:
    hint = (
        ""
        if registry_configured
        else (
            " If the topic is written through the Confluent Schema Registry, set "
            "DATACONTRACT_KAFKA_SCHEMA_REGISTRY_URL so that the schema the messages were written "
            "with is read from the registry instead of being derived from the data contract."
        )
    )
    return DataContractException(
        type="test",
        name="Configuring Kafka checks",
        result=ResultEnum.failed,
        reason=(
            f"Cannot decode the Avro messages of the topic with the schema from {source}. "
            f"Avro is positionally encoded, so it must be the exact schema the messages "
            f"were written with.{hint}"
        ),
        engine="datacontract-cli",
        original_exception=cause,
    )


def get_schema_registry_config(config: Config | None = None) -> Optional[dict]:
    """Confluent Schema Registry settings from the config or environment, or None if not configured."""
    config = Config.resolve(config)
    url = config.get_kafka_schema_registry_url()
    if not url:
        return None
    return {
        "url": url.rstrip("/"),
        "username": config.get_kafka_schema_registry_username(),
        "password": config.get_kafka_schema_registry_password(),
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
            engine="datacontract-cli",
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
            engine="datacontract-cli",
        )
    return body["schema"]


# ---------------------------------------------------------------------------
# json
# ---------------------------------------------------------------------------
def _decode_json(values: List[bytes], schema_obj: SchemaObject):
    """Decode JSON messages into the column types the data contract declares.

    A message that is not a JSON object becomes a row of nulls rather than an
    error, matching the permissive mode the Spark reader used: the checks then
    report it as missing values, which is what it is.
    """
    pa = _import("pyarrow")

    records = []
    for value in values:
        try:
            record = json.loads(value.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            record = None
        records.append(record if isinstance(record, dict) else {})

    return _records_to_arrow(pa, records, to_arrow_schema(pa, schema_obj.properties or []))


# ---------------------------------------------------------------------------
# arrow conversion
# ---------------------------------------------------------------------------
def _records_to_arrow(pa, records: List[dict], schema):
    """Build an arrow table of ``records`` shaped by ``schema``."""
    arrays = [_arrow_column(pa, [record.get(field.name) for record in records], field.type) for field in schema]
    return pa.Table.from_arrays(arrays, schema=schema)


def _arrow_column(pa, values: List[Any], arrow_type):
    """Convert a column of decoded values to ``arrow_type``, nulling what does not fit."""
    try:
        return pa.array(values, type=arrow_type)
    except (pa.ArrowInvalid, pa.ArrowTypeError, pa.ArrowNotImplementedError, ValueError, TypeError, OverflowError):
        pass
    try:
        # Values that need parsing rather than conversion, e.g. an ISO 8601 string
        # for a field the contract declares as a timestamp.
        return pa.array(values).cast(arrow_type, safe=False)
    except (pa.ArrowInvalid, pa.ArrowTypeError, pa.ArrowNotImplementedError, ValueError, TypeError, OverflowError):
        pass
    coerced = []
    for value in values:
        try:
            pa.array([value], type=arrow_type)
            coerced.append(value)
        except Exception:
            coerced.append(None)
    return pa.array(coerced, type=arrow_type)


def to_arrow_schema(pa, properties: List[SchemaProperty]):
    """Arrow schema for the properties a data contract declares.

    Every field is nullable: whether a value may be missing is what the required
    checks report on, so rejecting nulls here would turn a check result into a
    read error.
    """
    return pa.schema([pa.field(prop.name, to_arrow_type(pa, prop), nullable=True) for prop in properties])


def _get_type(prop: SchemaProperty) -> Optional[str]:
    """Get the type from a schema property. Prefers physicalType for accurate type checking."""
    if prop.physicalType:
        return prop.physicalType
    if prop.logicalType:
        return prop.logicalType
    return None


def _field_name(prop: SchemaProperty) -> str:
    return prop.physicalName or prop.name


def add_spark_nested_views(spark, model_name: str, properties: List[SchemaProperty] | None):
    """Create Spark temp views for nested struct fields and array-of-struct items.

    The engine-neutral recursive check builder targets array item checks at
    ``{model}__{array_field}``, mirroring the DuckDB nested-view convention.
    For struct fields, the executor resolves dotted paths against the parent
    model directly, but we still recurse here so arrays nested under structs can
    materialize their own item views.
    """
    if not properties:
        return

    try:
        from pyspark.sql import functions as F
    except ImportError as e:
        raise DataContractException(
            type="schema",
            result="failed",
            name="pyspark is missing",
            reason="Install the extra datacontract-cli[kafka] to use kafka",
            engine="datacontract",
            original_exception=e,
        )

    parent = spark.table(model_name)
    nested_alias = "__dc_nested__"
    for prop in properties:
        field_name = _field_name(prop)
        field_type = (_get_type(prop) or "").lower()

        if field_type in {"object", "record", "struct"} and prop.properties:
            child = parent.select(F.col(f"`{field_name}`").alias(nested_alias))
            if not prop.required:
                child = child.where(F.col(nested_alias).isNotNull())
            child.select(f"{nested_alias}.*").createOrReplaceTempView(f"{model_name}__{field_name}")
            add_spark_nested_views(spark, f"{model_name}__{field_name}", prop.properties)

        elif field_type == "array" and prop.items and prop.items.properties:
            child = parent
            if not prop.required:
                child = child.where(F.col(f"`{field_name}`").isNotNull())
            child = child.select(F.explode_outer(F.col(f"`{field_name}`")).alias(nested_alias))
            child.select(f"{nested_alias}.*").createOrReplaceTempView(f"{model_name}__{field_name}")
            add_spark_nested_views(spark, f"{model_name}__{field_name}", prop.items.properties)


def add_spark_nested_views_for_contract(spark, data_contract: OpenDataContractStandard, schema_name: str = "all"):
    if not data_contract.schema_:
        return
    for schema_obj in data_contract.schema_:
        model_name = schema_obj.physicalName or schema_obj.name
        if schema_name != "all" and schema_obj.name != schema_name:
            continue
        add_spark_nested_views(spark, model_name, schema_obj.properties)


def _decimal_params(prop: SchemaProperty) -> Tuple[int, int]:
    options = prop.logicalTypeOptions or {}
    precision = options.get("precision")
    scale = options.get("scale")
    # Wide enough to hold what a contract that says nothing about precision may carry.
    return int(precision) if precision else 38, int(scale) if scale is not None else 9


def to_arrow_type(pa, prop: SchemaProperty):
    """Map a data contract property to the arrow type its values are read as."""
    match _get_type(prop):
        case "string" | "varchar" | "text":
            return pa.string()
        case "number" | "decimal" | "numeric":
            return pa.decimal128(*_decimal_params(prop))
        case "float":
            return pa.float32()
        case "double":
            return pa.float64()
        case "integer" | "int":
            return pa.int32()
        case "long" | "bigint":
            return pa.int64()
        case "boolean":
            return pa.bool_()
        case "timestamp" | "timestamp_tz":
            return pa.timestamp("us", tz="UTC")
        case "timestamp_ntz":
            return pa.timestamp("us")
        case "date":
            return pa.date32()
        case "time":
            return pa.time64("us")
        case "object" | "record" | "struct":
            return pa.struct(to_arrow_schema(pa, prop.properties or []))
        case "binary":
            return pa.binary()
        case "array":
            items = prop.items
            if items is None:
                return pa.list_(pa.string())
            if items.properties:
                return pa.list_(pa.struct(to_arrow_schema(pa, items.properties)))
            return pa.list_(to_arrow_type(pa, items))
        case "null":
            return pa.null()
        case _:
            return pa.string()


_AVRO_PRIMITIVES = {
    "null": "null",
    "boolean": "bool_",
    "int": "int32",
    "long": "int64",
    "float": "float32",
    "double": "float64",
    "bytes": "binary",
    "string": "string",
}

# fastavro decodes these into the Python objects arrow expects for the matching type
# (datetime, date, time, Decimal), so the mapping is all that is needed.
_AVRO_LOGICAL_TYPES = {
    ("int", "date"): lambda pa, t: pa.date32(),
    ("int", "time-millis"): lambda pa, t: pa.time32("ms"),
    ("long", "time-micros"): lambda pa, t: pa.time64("us"),
    ("long", "timestamp-millis"): lambda pa, t: pa.timestamp("ms", tz="UTC"),
    ("long", "timestamp-micros"): lambda pa, t: pa.timestamp("us", tz="UTC"),
    ("long", "local-timestamp-millis"): lambda pa, t: pa.timestamp("ms"),
    ("long", "local-timestamp-micros"): lambda pa, t: pa.timestamp("us"),
    ("bytes", "decimal"): lambda pa, t: pa.decimal128(t.get("precision", 38), t.get("scale", 0)),
    ("fixed", "decimal"): lambda pa, t: pa.decimal128(t.get("precision", 38), t.get("scale", 0)),
}


def _avro_schema_to_arrow(pa, avro_schema: dict):
    return pa.schema(
        [
            pa.field(field["name"], _avro_type_to_arrow(pa, field["type"]), nullable=True)
            for field in avro_schema["fields"]
        ]
    )


def _avro_type_to_arrow(pa, avro_type):
    """Map an Avro schema node to the arrow type fastavro decodes it into."""
    if isinstance(avro_type, list):
        members = [member for member in avro_type if member != "null"]
        if not members:
            return pa.null()
        if len(members) == 1:
            return _avro_type_to_arrow(pa, members[0])
        raise DataContractException(
            type="test",
            name="Configuring Kafka checks",
            result=ResultEnum.failed,
            reason=(
                f"Avro unions of more than one non-null type are not supported: {avro_type}. "
                f"A column has one type, and which of the union's types a message carries is only "
                f"known per message."
            ),
            engine="datacontract-cli",
        )

    if isinstance(avro_type, dict):
        base = avro_type.get("type")
        logical = avro_type.get("logicalType")
        if (base, logical) in _AVRO_LOGICAL_TYPES:
            return _AVRO_LOGICAL_TYPES[(base, logical)](pa, avro_type)
        if base == "record":
            return pa.struct(_avro_schema_to_arrow(pa, avro_type))
        if base == "array":
            return pa.list_(_avro_type_to_arrow(pa, avro_type["items"]))
        if base == "map":
            return pa.map_(pa.string(), _avro_type_to_arrow(pa, avro_type["values"]))
        if base == "enum":
            return pa.string()
        if base == "fixed":
            return pa.binary(avro_type["size"])
        return _avro_type_to_arrow(pa, base)

    factory = _AVRO_PRIMITIVES.get(avro_type)
    if factory is None:
        raise DataContractException(
            type="test",
            name="Configuring Kafka checks",
            result=ResultEnum.failed,
            reason=f"Unsupported Avro type '{avro_type}' in the schema of the topic.",
            engine="datacontract-cli",
        )
    return getattr(pa, factory)()
