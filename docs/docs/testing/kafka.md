---
sidebar_position: 13
title: "Kafka"
description: "Create a data contract for a Kafka topic and test the messages against it (experimental)."
---

# <img className="page-icon" src="/img/icons/kafka.svg" alt="" /> Kafka

Test data in Kafka topics. Kafka support is currently considered **experimental**.

## 1. Install

```bash
uv tool install --python python3.11 --upgrade 'datacontract-cli[kafka]'
```

No Java runtime is needed: the topic is consumed and decoded in Python, and the checks run in DuckDB. See [Installation](../installation.md) for pip, pipx, and Docker.

## 2. Authenticate

Create a `.env` file in your working directory (or export the variables):

```bash
# .env
DATACONTRACT_KAFKA_SASL_USERNAME=mykey
DATACONTRACT_KAFKA_SASL_PASSWORD=mysecret
```

If no username/password is set, the CLI connects without authentication (e.g. a local broker).

If the topic is Avro-encoded through the Confluent Schema Registry, add the registry as well, so the messages are decoded with the schema they were actually written with:

```bash
DATACONTRACT_KAFKA_SCHEMA_REGISTRY_URL=https://psrc-12345.eu-central-1.aws.confluent.cloud
DATACONTRACT_KAFKA_SCHEMA_REGISTRY_USERNAME=myregistrykey
DATACONTRACT_KAFKA_SCHEMA_REGISTRY_PASSWORD=myregistrysecret
```

## 3. Create a contract for your topic

If you have an Avro schema for the topic (e.g. from a schema registry), import it:

```bash
datacontract import avro --source orders.avsc --output datacontract.yaml
```

Then add a `servers` entry pointing at your broker and topic:

```yaml
servers:
  - server: production
    type: kafka
    host: abc-12345.eu-central-1.aws.confluent.cloud:9092
    topic: my-topic-name
    format: json # or avro
```

## 4. Test the actual data

```bash
datacontract test datacontract.yaml
```

```
Testing datacontract.yaml
Server: production (type=kafka, format=json, host=abc-12345.eu-central-1.aws.confluent.cloud:9092)
╭────────┬─────────────────────────────────────────────────┬─────────────────┬─────────╮
│ Result │ Check                                           │ Field           │ Details │
├────────┼─────────────────────────────────────────────────┼─────────────────┼─────────┤
│ passed │ Check that field 'order_id' is present          │ orders.order_id │         │
│ passed │ Check that field order_id has no missing values │ orders.order_id │         │
│  ...   │                                                 │                 │         │
╰────────┴─────────────────────────────────────────────────┴─────────────────┴─────────╯
🟢 data contract is valid. Run 24 checks. Took 8.4 seconds.
```

## 5. Let it catch a violation

The contract becomes valuable when it detects drift. Tighten an expectation — for example, mark a field as `required: true` or restrict a field to its allowed values. Run `datacontract test datacontract.yaml` again: every violation is listed as an error, and the command exits with code `1` — ready for [CI/CD and scheduled runs](../scheduling/index.md) so you catch drift before your consumers do.

## Reference

All authentication options (SASL mechanisms) and the Avro data type mappings: **[Kafka Reference](../reference/kafka.md)**.

## Troubleshooting

- **Authentication failures against Confluent Cloud** — use an API key/secret as `SASL_USERNAME`/`SASL_PASSWORD` with the default `PLAIN` mechanism.
- **The test reads no messages** — the check consumes the topic from the beginning; verify the topic name in the `servers` block and that the topic contains messages in the declared `format`.
- **The test runs out of memory on a large topic** — every message is held in memory. Set `DATACONTRACT_KAFKA_MAX_MESSAGES` to check a sample of the topic instead; the run then reports that it read only part of it.
- **`Cannot decode the Avro messages of the topic`** — the schema used for decoding is not the one the messages were written with. For a topic produced through the Confluent Schema Registry, set `DATACONTRACT_KAFKA_SCHEMA_REGISTRY_URL`; otherwise re-import the contract from the topic's Avro schema with `datacontract import avro`.
