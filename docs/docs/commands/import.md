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

Available formats: `dbt`, `sql`, `avro`, `dbml`, `glue`, `bigquery`, `unity`, `jsonschema`, `json`, `odcs`, `parquet`, `csv`, `protobuf`, `spark`, `iceberg`, `excel`, `powerbi`, `snowflake`.
