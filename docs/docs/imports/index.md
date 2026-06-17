---
sidebar_position: 0
title: "Imports"
slug: /imports
description: "Create a data contract from an existing schema such as SQL DDL, dbt, BigQuery, Glue, or Excel."
---

# Imports

`datacontract import` creates a data contract from an existing source format. This is the fastest way to bootstrap a contract from a system you already have.

```bash
# Import from a SQL DDL file
datacontract import sql --source my_ddl.sql --dialect postgres

# Save the result to a file
datacontract import sql --source my_ddl.sql --dialect postgres --output datacontract.yaml
```

Run `datacontract import <format> --help` to see the format-specific options (e.g. `datacontract import sql --help`). If a format you need is missing, [open an issue on GitHub](https://github.com/datacontract/datacontract-cli/issues).

## Available importers

| Format | Description |
|---|---|
| [`sql`](./sql.md) | A SQL DDL file. |
| [`dbt`](./dbt.md) | A dbt manifest file. |
| [`avro`](./avro.md) | An Avro schema file. |
| [`dbml`](./dbml.md) | A DBML file. |
| [`glue`](./glue.md) | AWS Glue Data Catalog. |
| [`bigquery`](./bigquery.md) | Google BigQuery (file or API). |
| [`unity`](./unity.md) | Databricks Unity Catalog. |
| [`jsonschema`](./jsonschema.md) | A JSON Schema file. |
| [`json`](./json.md) | A JSON data file. |
| [`odcs`](./odcs.md) | An ODCS data contract file. |
| [`parquet`](./parquet.md) | A Parquet file. |
| [`csv`](./csv.md) | A CSV file. |
| [`protobuf`](./protobuf.md) | A Protobuf schema file. |
| [`spark`](./spark.md) | A Spark schema / DataFrame. |
| [`iceberg`](./iceberg.md) | An Iceberg schema. |
| [`excel`](./excel.md) | An ODCS Excel template. |
| [`powerbi`](./powerbi.md) | A Power BI semantic model (`.pbit`, `.bim`, or `.json`). |
| [`snowflake`](./snowflake.md) | A Snowflake workspace. |

See the [`import` command reference](../commands/import.md) for the common signature.
