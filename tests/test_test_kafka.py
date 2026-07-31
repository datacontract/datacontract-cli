import contextlib
import io
import json
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
import six

# Fix for Python 3.12
if sys.version_info >= (3, 12, 1):
    sys.modules["kafka.vendor.six.moves"] = six.moves


from kafka import KafkaProducer
from open_data_contract_standard.model import OpenDataContractStandard
from testcontainers.kafka import KafkaContainer

from datacontract.data_contract import DataContract
from datacontract.export.avro_exporter import to_avro_schema_json

datacontract = "fixtures/kafka/datacontract.yaml"
datacontract_avro = "fixtures/kafka/datacontract_avro.yaml"

# Skip when running under pytest-xdist workers - Spark's Java Kafka client
# experiences timeouts when running in xdist subprocess environment
is_xdist_worker = os.environ.get("PYTEST_XDIST_WORKER") is not None

CONFLUENT_SCHEMA_ID = 42

# What a Confluent Schema Registry typically holds for such a topic: every field is a
# ["null", T] union, the shape the Avro/Java serializers generate. It deliberately differs
# from the schema the data contract derives (there, required fields are plain types), so
# messages written with it cannot be decoded with the contract's schema.
CONFLUENT_WRITER_SCHEMA = json.dumps(
    {
        "type": "record",
        "name": "inventory",
        "fields": [
            {"name": "updated_at", "type": ["null", "string"], "default": None},
            {"name": "available", "type": ["null", "int"], "default": None},
            {"name": "location", "type": ["null", "string"], "default": None},
            {"name": "sku", "type": ["null", "string"], "default": None},
        ],
    }
)


@pytest.mark.skipif(is_xdist_worker, reason="Spark Kafka tests fail under pytest-xdist workers")
def test_test_kafka(monkeypatch):
    monkeypatch.delenv("DATACONTRACT_KAFKA_SASL_USERNAME", raising=False)

    with KafkaContainer("confluentinc/cp-kafka:7.7.0").with_kraft() as kafka:
        send_messages_to_topic(kafka, "fixtures/kafka/data/messages.json", "inventory-events")
        data_contract_str = _setup_datacontract(kafka)
        data_contract = DataContract(data_contract_str=data_contract_str)
        run = data_contract.test()

    print(run.pretty())
    assert run.result == "passed"


@pytest.mark.skipif(is_xdist_worker, reason="Spark Kafka tests fail under pytest-xdist workers")
def test_test_kafka_avro_plain(monkeypatch):
    """Plain Avro messages (no Confluent Schema Registry framing) must decode without
    being corrupted by the 5-byte magic-byte/schema-id strip. Regression for #1344,
    where every field was reported as null (missing_count == row count)."""
    monkeypatch.delenv("DATACONTRACT_KAFKA_SASL_USERNAME", raising=False)

    with KafkaContainer("confluentinc/cp-kafka:7.7.0").with_kraft() as kafka:
        send_avro_messages_to_topic(kafka, "fixtures/kafka/data/messages.json", "inventory-events-avro")
        data_contract_str = _setup_datacontract(kafka, datacontract_avro)
        data_contract = DataContract(data_contract_str=data_contract_str)
        run = data_contract.test()

    print(run.pretty())
    assert run.result == "passed"


@pytest.mark.skipif(is_xdist_worker, reason="Spark Kafka tests fail under pytest-xdist workers")
def test_test_kafka_avro_confluent_schema_registry(monkeypatch):
    """Confluent-framed Avro messages must be decoded with the writer schema from the schema
    registry, not with the schema derived from the data contract. Regression for #1347, where
    every field of every message was reported as null."""
    monkeypatch.delenv("DATACONTRACT_KAFKA_SASL_USERNAME", raising=False)

    with (
        KafkaContainer("confluentinc/cp-kafka:7.7.0").with_kraft() as kafka,
        schema_registry_stub({CONFLUENT_SCHEMA_ID: CONFLUENT_WRITER_SCHEMA}) as registry_url,
    ):
        monkeypatch.setenv("DATACONTRACT_KAFKA_SCHEMA_REGISTRY_URL", registry_url)
        send_confluent_avro_messages_to_topic(kafka, "fixtures/kafka/data/messages.json", "inventory-events-avro")
        data_contract_str = _setup_datacontract(kafka, datacontract_avro)
        data_contract = DataContract(data_contract_str=data_contract_str)
        run = data_contract.test()

    print(run.pretty())
    assert run.result == "passed"


@pytest.mark.skipif(is_xdist_worker, reason="Spark Kafka tests fail under pytest-xdist workers")
def test_test_kafka_avro_confluent_without_schema_registry(monkeypatch):
    """Without a configured registry the writer schema of Confluent-framed messages is unknown.
    That must be reported as an undecodable topic rather than silently decoding every message
    into a record of nulls, which looked like missing values on data that is not null (#1347)."""
    monkeypatch.delenv("DATACONTRACT_KAFKA_SASL_USERNAME", raising=False)
    monkeypatch.delenv("DATACONTRACT_KAFKA_SCHEMA_REGISTRY_URL", raising=False)

    with KafkaContainer("confluentinc/cp-kafka:7.7.0").with_kraft() as kafka:
        send_confluent_avro_messages_to_topic(kafka, "fixtures/kafka/data/messages.json", "inventory-events-avro")
        data_contract_str = _setup_datacontract(kafka, datacontract_avro)
        data_contract = DataContract(data_contract_str=data_contract_str)
        run = data_contract.test()

    print(run.pretty())
    assert run.result == "failed"
    reasons = " ".join(check.reason or "" for check in run.checks)
    assert "Cannot decode the Avro messages" in reasons
    assert "DATACONTRACT_KAFKA_SCHEMA_REGISTRY_URL" in reasons


@contextlib.contextmanager
def schema_registry_stub(schemas: dict):
    """Serve the Confluent Schema Registry endpoint the CLI uses: GET /schemas/ids/{id}."""

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            schema = schemas.get(int(self.path.rsplit("/", 1)[-1]))
            body = json.dumps({"schema": schema}).encode() if schema else b"{}"
            self.send_response(200 if schema else 404)
            self.send_header("Content-Type", "application/vnd.schemaregistry.v1+json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()


def send_confluent_avro_messages_to_topic(kafka: KafkaContainer, messages_file_path: str, topic_name: str):
    """Publish the JSON sample records as Confluent-framed Avro: magic byte 0x00, the 4-byte
    schema id, then the payload written with the registry's (not the contract's) schema."""
    from avro.io import BinaryEncoder, DatumWriter
    from avro.schema import parse as parse_avro_schema

    print(f"Sending Confluent-framed Avro messages from {messages_file_path} to Kafka topic {topic_name}")

    bootstrap_server = kafka.get_bootstrap_server().replace("localhost", "127.0.0.1")
    _ensure_topic_exists(bootstrap_server, topic_name)

    writer = DatumWriter(parse_avro_schema(CONFLUENT_WRITER_SCHEMA))

    def encode(record: dict) -> bytes:
        buffer = io.BytesIO()
        buffer.write(b"\x00" + CONFLUENT_SCHEMA_ID.to_bytes(4, "big"))
        writer.write(record, BinaryEncoder(buffer))
        return buffer.getvalue()

    producer = KafkaProducer(bootstrap_servers=bootstrap_server, value_serializer=encode)
    messages_sent = 0
    with open(messages_file_path) as messages_file:
        for line in messages_file:
            producer.send(topic=topic_name, value=json.loads(line))
            messages_sent += 1

    producer.flush()
    producer.close()
    print(f"Sent {messages_sent} Confluent-framed Avro messages from {messages_file_path} to topic {topic_name}")


def send_avro_messages_to_topic(kafka: KafkaContainer, messages_file_path: str, topic_name: str):
    """Serialize the JSON sample records as plain Avro (no Confluent prefix) and publish them."""
    from avro.io import BinaryEncoder, DatumWriter
    from avro.schema import parse as parse_avro_schema

    print(f"Sending Avro messages from {messages_file_path} to Kafka topic {topic_name}")

    bootstrap_server = kafka.get_bootstrap_server().replace("localhost", "127.0.0.1")
    _ensure_topic_exists(bootstrap_server, topic_name)

    with open(datacontract_avro) as data_contract_file:
        odcs = OpenDataContractStandard.from_string(data_contract_file.read())
    schema_obj = odcs.schema_[0]
    avro_schema = parse_avro_schema(to_avro_schema_json(schema_obj.name, schema_obj))
    writer = DatumWriter(avro_schema)

    def encode(record: dict) -> bytes:
        buffer = io.BytesIO()
        writer.write(record, BinaryEncoder(buffer))
        return buffer.getvalue()

    producer = KafkaProducer(bootstrap_servers=bootstrap_server, value_serializer=encode)
    messages_sent = 0
    with open(messages_file_path) as messages_file:
        for line in messages_file:
            producer.send(topic=topic_name, value=json.loads(line))
            messages_sent += 1

    producer.flush()
    producer.close()
    print(f"Sent {messages_sent} Avro messages from {messages_file_path} to Kafka topic {topic_name}")


def send_messages_to_topic(kafka: KafkaContainer, messages_file_path: str, topic_name: str):
    print(f"Sending messages from {messages_file_path} to Kafka topic {topic_name}")

    bootstrap_server = kafka.get_bootstrap_server().replace("localhost", "127.0.0.1")

    # Pre-create the topic and wait for it to be ready
    # This prevents race conditions with Spark trying to read before topic metadata is available
    _ensure_topic_exists(bootstrap_server, topic_name)

    producer = KafkaProducer(bootstrap_servers=bootstrap_server, value_serializer=lambda v: v.encode("utf-8"))
    messages_sent = 0

    with open(messages_file_path) as messages_file:
        for line in messages_file:
            message = line
            producer.send(topic=topic_name, value=message)
            messages_sent += 1

    producer.flush()
    producer.close()

    print(f"Sent {messages_sent} messages from {messages_file_path} to Kafka topic {topic_name}")


def _ensure_topic_exists(bootstrap_server: str, topic_name: str, timeout_seconds: int = 30):
    """Create topic and wait for it to be fully available in cluster metadata."""
    from kafka import KafkaConsumer
    from kafka.admin import KafkaAdminClient, NewTopic
    from kafka.errors import TopicAlreadyExistsError

    admin = KafkaAdminClient(bootstrap_servers=bootstrap_server)
    try:
        admin.create_topics([NewTopic(name=topic_name, num_partitions=1, replication_factor=1)])
    except TopicAlreadyExistsError:
        pass
    finally:
        admin.close()

    # Wait for topic to appear in metadata
    consumer = KafkaConsumer(bootstrap_servers=bootstrap_server)
    start_time = time.time()
    while time.time() - start_time < timeout_seconds:
        topics = consumer.topics()
        if topic_name in topics:
            consumer.close()
            print(f"Topic {topic_name} is ready")
            return
        time.sleep(0.1)
    consumer.close()
    raise TimeoutError(f"Topic {topic_name} not available after {timeout_seconds}s")


def _setup_datacontract(kafka: KafkaContainer, contract_path: str = datacontract):
    with open(contract_path) as data_contract_file:
        data_contract_str = data_contract_file.read()
    host = kafka.get_bootstrap_server()
    # Replace localhost with 127.0.0.1 to avoid IPv4/IPv6 resolution issues
    # that can cause timeouts in Spark's Kafka client under parallel load
    host = host.replace("localhost", "127.0.0.1")
    return data_contract_str.replace("__KAFKA_HOST__", host)
