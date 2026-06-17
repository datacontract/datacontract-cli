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

Available formats: `sql`, `sql-query`, `dbt-models`, `dbt-sources`, `dbt-staging-sql`, `avro`, `avro-idl`, `jsonschema`, `pydantic-model`, `protobuf`, `odcs`, `rdf`, `html`, `markdown`, `mermaid`, `bigquery`, `dbml`, `go`, `spark`, `sqlalchemy`, `iceberg`, `sodacl`, `great-expectations`, `data-caterer`, `dcs`, `dqx`, `excel`, `custom`.
