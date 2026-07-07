---
sidebar_position: 10
title: "Kafka"
description: "Test data in Kafka topics (experimental)."
---

<img className="page-icon" src="/img/icons/kafka.svg" alt="" />

# Kafka

:::info[Required extra]
This connection requires the `kafka` extra. See [Installation](../installation.md).
:::

Test data in Kafka topics. Kafka support is currently considered **experimental**.

## Server

```yaml
servers:
  - server: production
    type: kafka
    host: abc-12345.eu-central-1.aws.confluent.cloud:9092
    topic: my-topic-name
    format: json
```

## Environment variables

| Variable | Example | Description |
|---|---|---|
| `DATACONTRACT_KAFKA_SASL_USERNAME` | `xxx` | The SASL username (key) |
| `DATACONTRACT_KAFKA_SASL_PASSWORD` | `xxx` | The SASL password (secret) |
| `DATACONTRACT_KAFKA_SASL_MECHANISM` | `PLAIN` | Default `PLAIN`; also `SCRAM-SHA-256`, `SCRAM-SHA-512` |

