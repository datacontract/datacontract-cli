import sys

import six

# Fix for Python 3.12
if sys.version_info >= (3, 12, 1):
    sys.modules["kafka.vendor.six.moves"] = six.moves

import json
import logging

import pytest
from kafka import KafkaProducer
from testcontainers.kafka import KafkaContainer

from datacontract.data_contract import DataContract

logging.basicConfig(level=logging.INFO, force=True)

datacontract = "fixtures/kafka/datacontract.yaml"

kafka = KafkaContainer("confluentinc/cp-kafka:7.6.1")


@pytest.fixture(scope="module", autouse=True)
def kafka_container(request):
    kafka.start()

    def remove_container():
        kafka.stop()

    request.addfinalizer(remove_container)


def test_test_kafka(kafka_container: KafkaContainer):
    send_messages_to_topic("fixtures/kafka/data/messages.json", "inventory-events")
    data_contract_str = _setup_datacontract()
    data_contract = DataContract(data_contract_str=data_contract_str)

    run = data_contract.test()

    print(run)
    assert run.result == "passed"


def send_messages_to_topic(messages_file_path: str, topic_name: str):
    print(f"Sending messages from {messages_file_path} to Kafka topic {topic_name}")

    producer = KafkaProducer(
        bootstrap_servers=kafka.get_bootstrap_server(), value_serializer=lambda m: json.dumps(m).encode("ascii")
    )
    messages_sent = 0

    with open(messages_file_path) as messages_file:
        for line in messages_file:
            message = json.loads(line)
            producer.send(topic_name, message)
            messages_sent += 1

    producer.flush()
    print(f"Sent {messages_sent} messages from {messages_file_path} to Kafka topic {topic_name}")


def _setup_datacontract():
    with open(datacontract) as data_contract_file:
        data_contract_str = data_contract_file.read()
    host = kafka.get_bootstrap_server()
    return data_contract_str.replace("__KAFKA_HOST__", host)
