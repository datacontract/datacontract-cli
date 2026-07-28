---
sidebar_position: 8
title: "export"
description: "Convert a data contract to a target format."
---

# `datacontract export`

Convert a data contract to a target format. See the [Exports](../exports/index.md) section for every format and its options.

```bash
datacontract export <format> [LOCATION] [--output FILE] [--server NAME] [--schema-name NAME]
```

Run `datacontract export <format> --help` to see format-specific options.

```bash
datacontract export html datacontract.yaml --output datacontract.html
```

For SQL dialects (`postgres`, `mysql`, `snowflake`, `databricks`, `sqlserver`, `trino`, `oracle`, `clickhouse`), use `datacontract export sql --dialect <dialect>`.

Available formats: `avro`, `avro-idl`, `bigquery`, `custom`, `data-caterer`, `dbml`, `dbt-models`, `dbt-sources`, `dbt-staging-sql`, `dcs`, `dqx`, `excel`, `go`, `great-expectations`, `html`, `iceberg`, `jsonschema`, `markdown`, `mermaid`, `odcs`, `protobuf`, `pydantic-model`, `rdf`, `sodacl`, `spark`, `sql`, `sql-query`, `sqlalchemy`.
