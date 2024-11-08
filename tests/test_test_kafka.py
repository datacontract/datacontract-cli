import sys

import six

# Fix for Python 3.12
if sys.version_info >= (3, 12, 1):
    sys.modules["kafka.vendor.six.moves"] = six.moves


from kafka import KafkaProducer
from testcontainers.kafka import KafkaContainer

from datacontract.data_contract import DataContract

datacontract = "fixtures/kafka/datacontract.yaml"


def test_test_kafka(monkeypatch):
    monkeypatch.delenv("DATACONTRACT_KAFKA_SASL_USERNAME", raising=False)

    with KafkaContainer("confluentinc/cp-kafka:7.7.0").with_kraft() as kafka:
        send_messages_to_topic(kafka, "fixtures/kafka/data/messages.json", "inventory-events")
        data_contract_str = _setup_datacontract(kafka)
        data_contract = DataContract(data_contract_str=data_contract_str)
        run = data_contract.test()

    print(run.pretty())
    assert run.result == "passed"


def send_messages_to_topic(kafka: KafkaContainer, messages_file_path: str, topic_name: str):
    print(f"Sending messages from {messages_file_path} to Kafka topic {topic_name}")

    producer = KafkaProducer(
        bootstrap_servers=kafka.get_bootstrap_server(), value_serializer=lambda v: v.encode("utf-8")
    )
    messages_sent = 0

    with open(messages_file_path) as messages_file:
        for line in messages_file:
            message = line
            producer.send(topic=topic_name, value=message)
            messages_sent += 1
            producer.flush()

    print(f"Sent {messages_sent} messages from {messages_file_path} to Kafka topic {topic_name}")


def _setup_datacontract(kafka: KafkaContainer):
    with open(datacontract) as data_contract_file:
        data_contract_str = data_contract_file.read()
    host = kafka.get_bootstrap_server()
    return data_contract_str.replace("__KAFKA_HOST__", host)
