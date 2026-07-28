---
sidebar_position: 9
title: "import"
description: "Create a data contract from a source format."
---

# `datacontract import`

Create a data contract from a source format. See the [Imports](../imports/index.md) section for every format and its options.

```bash
datacontract import <format> --source <source> [--output FILE]
```

Run `datacontract import <format> --help` to see format-specific options.

```bash
datacontract import sql --source ddl.sql --dialect postgres --output datacontract.yaml
```

Available formats: `adls`, `athena`, `avro`, `bigquery`, `csv`, `databricks`, `dbml`, `dbt`, `excel`, `gcs`, `glue`, `iceberg`, `json`, `jsonschema`, `mysql`, `odcs`, `oracle`, `parquet`, `postgres`, `powerbi`, `protobuf`, `redshift`, `s3`, `snowflake`, `spark`, `sql`, `sqlserver`.
