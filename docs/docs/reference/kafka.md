---
sidebar_position: 10
title: "Kafka Reference"
sidebar_label: "Kafka"
description: "All Kafka authentication options and data type mappings."
---

# <img className="page-icon" src="/img/icons/kafka.svg" alt="" /> Kafka Reference

Authentication options and data type handling for [Kafka connections](../testing/kafka.md).

## Server

```yaml
servers:
  - server: production
    type: kafka
    host: abc-12345.eu-central-1.aws.confluent.cloud:9092
    topic: orders
    format: json # or avro
```

## Authentication

| Variable | Example | Description |
|---|---|---|
| `DATACONTRACT_KAFKA_SASL_USERNAME` | `xxx` | The SASL username (key) |
| `DATACONTRACT_KAFKA_SASL_PASSWORD` | `xxx` | The SASL password (secret) |
| `DATACONTRACT_KAFKA_SASL_MECHANISM` | `PLAIN` | Default `PLAIN`; also `SCRAM-SHA-256`, `SCRAM-SHA-512` |

If no username/password is set, the CLI connects without authentication (e.g. a local broker). `host`, `topic`, and `format` come from the contract's `servers` block. A username and password switch the connection to `SASL_SSL`.

## Reading the topic

| Variable | Example | Description |
|---|---|---|
| `DATACONTRACT_KAFKA_MAX_MESSAGES` | `100000` | Stop after this many messages. Unset by default: the whole topic is read |
| `DATACONTRACT_KAFKA_TIMEOUT` | `30` | Seconds to wait for a message before giving up. Default `30`; the timer resets whenever a message arrives, so a slow read is never cut short |
| `DATACONTRACT_KAFKA_GROUP_PREFIX` | `my-team-` | Replaces the default `datacontract-cli-` consumer group prefix. A UUID is still appended so each run gets a unique group ID. Useful when the service account's ACLs restrict which consumer group prefixes it may use |

Every partition is read from its earliest offset up to the latest offset at the time the run starts, so messages produced while the checks are running are not included. Offsets are never committed, and each run uses its own consumer group, so testing a topic does not disturb a real consumer. Messages with no value (compaction tombstones) are skipped.

All messages are held in memory. `DATACONTRACT_KAFKA_MAX_MESSAGES` bounds that on a large topic, at the cost of checking a sample rather than the whole topic — the run reports when it has done so.

## Schema Registry

For `format: avro`, the messages have to be decoded with the exact Avro schema they were _written_ with — Avro is positionally encoded, so a schema that merely looks similar decodes to garbage. Topics written through the Confluent Schema Registry carry the id of that schema in a 5-byte prefix on every message. Point the CLI at the registry so it resolves the id, instead of falling back to the schema derived from the data contract:

| Variable | Example | Description |
|---|---|---|
| `DATACONTRACT_KAFKA_SCHEMA_REGISTRY_URL` | `https://psrc-12345.eu-central-1.aws.confluent.cloud` | The schema registry base URL |
| `DATACONTRACT_KAFKA_SCHEMA_REGISTRY_USERNAME` | `xxx` | The registry API key (optional) |
| `DATACONTRACT_KAFKA_SCHEMA_REGISTRY_PASSWORD` | `xxx` | The registry API secret (optional) |

Messages without the prefix (plain Avro) are decoded with the schema derived from the data contract, so a topic that mixes both still works, as does a topic whose schema evolved across several registry ids.

## Data types

### Importing

For Avro-encoded topics, import the schema with `datacontract import avro`. The Avro type is kept as `physicalType`:

| Avro type | `logicalType` |
|---|---|
| `string` | `string` |
| `int`, `long` | `integer` |
| `float`, `double` | `number` |
| `boolean` | `boolean` |
| `record` | `object` with nested `properties` |
| `array` | `array` |
| `map` | `object` (values not expanded) |
| `enum` | `string` (symbols in the `avroSymbols` custom property) |
| `bytes`, `fixed` | `array` |

Avro logical type annotations take precedence: `decimal` → `number` (with precision/scale), `date` → `date`, `uuid`/`duration`/`time-millis`/`time-micros` → `string`. Unions must be `[null, T]` and make the field optional.

### Testing

For `format: json` and `format: avro`, no type checks are generated — violations surface as decode errors or as value-check failures from `logicalTypeOptions`.

JSON messages are decoded as the types the contract declares; a message that is not a JSON object becomes a row of nulls and is reported as missing values. Avro messages are decoded with the schema they were written with — from the [schema registry](#schema-registry) when the message carries a schema id, otherwise the one derived from the contract — and keep that schema's types:

| Avro type | Read as |
|---|---|
| `boolean` | `BOOLEAN` |
| `int`, `long` | `INTEGER`, `BIGINT` |
| `float`, `double` | `FLOAT`, `DOUBLE` |
| `string`, `enum` | `VARCHAR` |
| `bytes`, `fixed` | `BLOB` |
| `record` | `STRUCT` |
| `array` | `LIST` |
| `map` | `MAP(VARCHAR, …)` |
| `decimal` (on `bytes`/`fixed`) | `DECIMAL(precision, scale)` |
| `date` | `DATE` |
| `time-millis`, `time-micros` | `TIME` |
| `timestamp-millis`, `timestamp-micros` | `TIMESTAMP WITH TIME ZONE` |
| `local-timestamp-millis`, `local-timestamp-micros` | `TIMESTAMP` |

A union must be `[null, T]`: which type of a wider union a message carries is known only per message, and a column has one type. Such a union is rejected with an error rather than guessed at.
