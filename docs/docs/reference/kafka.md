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

If no username/password is set, the CLI connects without authentication (e.g. a local broker). `host`, `topic`, and `format` come from the contract's `servers` block. Kafka checks run on Spark and require a JDK (17 or 21).

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

Messages are read via Spark. For `format: json` and `format: avro`, no type checks are generated — messages are decoded as the contract's types, and violations surface as decode errors or value-check failures from `logicalTypeOptions`.
