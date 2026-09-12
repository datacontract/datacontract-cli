"""Unit tests for the pieces of the Kafka reader that need no broker."""

import io
import json

import fastavro
import pyarrow as pa
import pytest
from open_data_contract_standard.model import SchemaObject, SchemaProperty

from datacontract.config import Config
from datacontract.engines.ibis.connections.kafka import (
    _avro_type_to_arrow,
    _consumer_config,
    _decode_json,
    _group_by_writer_schema,
    get_auth_options,
    to_arrow_type,
)
from datacontract.model.exceptions import DataContractException


def _mock_server():
    from unittest.mock import MagicMock

    server = MagicMock()
    server.host = "localhost:9092"
    return server


def test_consumer_config_uses_default_prefix_when_unset():
    result = _consumer_config(_mock_server(), Config())
    assert result["group.id"].startswith("datacontract-cli-")


def test_consumer_config_uses_custom_prefix():
    result = _consumer_config(_mock_server(), Config(kafka_group_prefix="my-team-"))
    assert result["group.id"].startswith("my-team-")
    assert not result["group.id"].startswith("datacontract-cli-")


def test_auth_options_are_empty_without_credentials():
    assert get_auth_options(Config()) == {}


def test_auth_options_use_sasl_ssl():
    options = get_auth_options(Config(kafka_sasl_username="key", kafka_sasl_password="secret"))

    assert options == {
        "security.protocol": "SASL_SSL",
        "sasl.mechanism": "PLAIN",
        "sasl.username": "key",
        "sasl.password": "secret",
    }


def test_auth_options_accept_scram():
    options = get_auth_options(
        Config(kafka_sasl_username="key", kafka_sasl_password="secret", kafka_sasl_mechanism="scram-sha-512")
    )

    assert options["sasl.mechanism"] == "SCRAM-SHA-512"


def test_auth_options_reject_an_unsupported_mechanism():
    with pytest.raises(ValueError, match="GSSAPI"):
        get_auth_options(Config(kafka_sasl_username="key", kafka_sasl_password="secret", kafka_sasl_mechanism="GSSAPI"))


def _framed(schema_id: int, payload: bytes) -> bytes:
    return b"\x00" + schema_id.to_bytes(4, "big") + payload


def test_plain_messages_keep_their_first_bytes():
    """A plain Avro record may well start with 0x00 (a null union branch); stripping
    five bytes from it would corrupt every field (#1344)."""
    messages = [b"\x00\x01\x02", b"plain"]

    assert _group_by_writer_schema(messages, registry=None) == [(None, [b"\x00\x01\x02", b"plain"])]


def test_confluent_framed_messages_group_by_schema_id():
    messages = [_framed(1, b"a"), _framed(2, b"b"), _framed(1, b"c"), b"unframed-message"]

    groups = _group_by_writer_schema(messages, registry={"url": "http://registry"})

    assert groups == [(None, [b"unframed-message"]), (1, [b"a", b"c"]), (2, [b"b"])]


def test_confluent_framed_messages_without_a_registry_are_an_error():
    with pytest.raises(DataContractException) as excinfo:
        _group_by_writer_schema([_framed(1, b"payload-long-enough")], registry=None)

    assert "Cannot decode the Avro messages" in excinfo.value.reason
    assert "DATACONTRACT_KAFKA_SCHEMA_REGISTRY_URL" in excinfo.value.reason


@pytest.mark.parametrize(
    "avro_type, expected",
    [
        ("string", pa.string()),
        ("long", pa.int64()),
        (["null", "int"], pa.int32()),
        (["int", "null"], pa.int32()),
        ({"type": "long", "logicalType": "timestamp-micros"}, pa.timestamp("us", tz="UTC")),
        ({"type": "long", "logicalType": "local-timestamp-millis"}, pa.timestamp("ms")),
        ({"type": "int", "logicalType": "date"}, pa.date32()),
        ({"type": "bytes", "logicalType": "decimal", "precision": 9, "scale": 2}, pa.decimal128(9, 2)),
        ({"type": "enum", "name": "color", "symbols": ["red"]}, pa.string()),
        ({"type": "fixed", "name": "md5", "size": 16}, pa.binary(16)),
        ({"type": "array", "items": "string"}, pa.list_(pa.string())),
        ({"type": "map", "values": "long"}, pa.map_(pa.string(), pa.int64())),
    ],
)
def test_avro_types_map_to_what_fastavro_decodes_them_into(avro_type, expected):
    assert _avro_type_to_arrow(pa, avro_type) == expected


def test_avro_unions_of_several_types_are_rejected():
    """Which member of the union a message carries is known per message, but a column
    has one type, so guessing one would silently drop the others."""
    with pytest.raises(DataContractException, match="unions of more than one non-null type"):
        _avro_type_to_arrow(pa, ["string", "long"])


@pytest.mark.parametrize(
    "logical_type, expected",
    [
        ("string", pa.string()),
        ("integer", pa.int32()),
        ("long", pa.int64()),
        ("double", pa.float64()),
        ("boolean", pa.bool_()),
        ("date", pa.date32()),
        ("timestamp", pa.timestamp("us", tz="UTC")),
        ("timestamp_ntz", pa.timestamp("us")),
    ],
)
def test_contract_types_map_to_arrow(logical_type, expected):
    assert to_arrow_type(pa, SchemaProperty(name="field", logicalType=logical_type)) == expected


def test_decimal_precision_and_scale_come_from_the_contract():
    prop = SchemaProperty(name="amount", logicalType="number", logicalTypeOptions={"precision": 12, "scale": 4})

    assert to_arrow_type(pa, prop) == pa.decimal128(12, 4)


def _inventory_schema() -> SchemaObject:
    return SchemaObject(
        name="inventory",
        properties=[
            SchemaProperty(name="sku", logicalType="string"),
            SchemaProperty(name="available", logicalType="integer"),
        ],
    )


def test_json_messages_are_decoded_as_the_contract_types():
    messages = [json.dumps({"sku": "abc", "available": 3}).encode()]

    table = _decode_json(messages, _inventory_schema())

    assert table.schema.types == [pa.string(), pa.int32()]
    assert table.to_pylist() == [{"sku": "abc", "available": 3}]


def test_a_message_that_is_not_a_json_object_becomes_a_row_of_nulls():
    """Rather than failing the whole read: the checks then report it as missing values,
    which is what it is."""
    messages = [b"not json at all", json.dumps({"sku": "abc", "available": 3}).encode()]

    table = _decode_json(messages, _inventory_schema())

    assert table.to_pylist() == [{"sku": None, "available": None}, {"sku": "abc", "available": 3}]


def test_a_json_value_that_does_not_fit_its_column_becomes_null():
    messages = [json.dumps({"sku": "abc", "available": "not-a-number"}).encode()]

    table = _decode_json(messages, _inventory_schema())

    assert table.to_pylist() == [{"sku": "abc", "available": None}]


def test_an_empty_topic_still_has_the_contract_columns():
    table = _decode_json([], _inventory_schema())

    assert table.num_rows == 0
    assert table.column_names == ["sku", "available"]


def test_avro_records_decode_with_the_types_of_their_writer_schema(monkeypatch):
    """A registry schema decides the column types, not the contract: an Avro topic is
    read as what it actually holds."""
    from datacontract.engines.ibis.connections import kafka as kafka_module

    writer_schema = {
        "type": "record",
        "name": "inventory",
        "fields": [
            {"name": "sku", "type": ["null", "string"], "default": None},
            {"name": "available", "type": "long"},
        ],
    }
    monkeypatch.setattr(kafka_module, "fetch_writer_schema", lambda registry, schema_id: json.dumps(writer_schema))
    parsed = fastavro.parse_schema(writer_schema)

    def encode(record):
        buffer = io.BytesIO()
        fastavro.schemaless_writer(buffer, parsed, record)
        return _framed(7, buffer.getvalue())

    messages = [encode({"sku": "abc", "available": 3}), encode({"sku": None, "available": 4})]

    table = kafka_module._decode_avro(
        messages, "inventory", _inventory_schema(), Config(kafka_schema_registry_url="http://registry")
    )

    # `long`, not the `integer` the contract declares for `available`
    assert table.schema.types == [pa.string(), pa.int64()]
    assert table.to_pylist() == [{"sku": "abc", "available": 3}, {"sku": None, "available": 4}]


def test_avro_messages_that_do_not_match_the_schema_are_reported_as_undecodable():
    from datacontract.engines.ibis.connections.kafka import _decode_avro

    with pytest.raises(DataContractException) as excinfo:
        _decode_avro([b"\x01\x02\x03\x04"], "inventory", _inventory_schema(), Config())

    assert "Cannot decode the Avro messages" in excinfo.value.reason
    assert "DATACONTRACT_KAFKA_SCHEMA_REGISTRY_URL" in excinfo.value.reason
