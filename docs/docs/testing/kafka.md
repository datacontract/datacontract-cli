---
sidebar_position: 10
title: "Kafka"
description: "Create a data contract for a Kafka topic and test the messages against it (experimental)."
---

# <img className="page-icon" src="/img/icons/kafka.svg" alt="" /> Kafka

Test data in Kafka topics. Kafka support is currently considered **experimental**.

## 1. Install

```bash
uv tool install --python python3.11 --upgrade 'datacontract-cli[kafka]'
```

Kafka checks run on Spark, which requires a **Java runtime (JDK 17 or 21)** — make sure `java` is on the path or `JAVA_HOME` is set. See [Installation](../installation.md) for pip, pipx, and Docker.

## 2. Set credentials

Create a `.env` file in your working directory (or export the variables):

```bash
# .env
DATACONTRACT_KAFKA_SASL_USERNAME=mykey
DATACONTRACT_KAFKA_SASL_PASSWORD=mysecret
```

If no username/password is set, the CLI connects without authentication (e.g. a local broker).

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
🟢 data contract is valid. Run 14 checks. Took 12.5 seconds.
```

## 5. Let it catch a violation

The contract becomes valuable when it detects drift. Tighten an expectation — for example, mark a field as `required: true` or restrict a field to its allowed values. Run `datacontract test datacontract.yaml` again: every violation is listed as an error, and the command exits with code `1` — ready for [CI/CD scheduling](../ci-cd.md) so you catch drift before your consumers do.

## Reference

All authentication options (SASL mechanisms) and the Avro data type mappings: **[Kafka Reference](../reference/kafka.md)**.

## Troubleshooting

- **`JAVA_HOME is not set` / `Unable to locate a Java Runtime`** — install a JDK (17 or 21) and set `JAVA_HOME`; the Kafka checks run on Spark.
- **Authentication failures against Confluent Cloud** — use an API key/secret as `SASL_USERNAME`/`SASL_PASSWORD` with the default `PLAIN` mechanism.
- **The test reads no messages** — the check consumes the topic from the beginning; verify the topic name in the `servers` block and that the topic contains messages in the declared `format`.
