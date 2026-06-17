---
sidebar_position: 0
title: "Exports"
slug: /exports
description: "Convert a data contract to SQL DDL, dbt, Avro, JSON Schema, HTML, Protobuf, and 20+ other formats."
---

# Exports

`datacontract export` converts a data contract to a target format. Use it to generate DDL, schemas, models, documentation, and data-quality artifacts directly from the contract.

```bash
datacontract export html datacontract.yaml --output datacontract.html
```

Run `datacontract export <format> --help` to see the format-specific options (e.g. `datacontract export sql --help`). If a format you need is missing, [open an issue on GitHub](https://github.com/datacontract/datacontract-cli/issues).

For SQL dialects (`postgres`, `mysql`, `snowflake`, `databricks`, `sqlserver`, `trino`, `oracle`, `clickhouse`), use `datacontract export sql --dialect <dialect>`.

## Available exporters

| Format | Description |
|---|---|
| [`sql`](./sql.md) | SQL DDL (`CREATE TABLE`). |
| [`sql-query`](./sql-query.md) | A SQL `SELECT` query. |
| [`dbt-models`](./dbt-models.md) | dbt model schema YAML. |
| [`dbt-sources`](./dbt-sources.md) | dbt sources YAML. |
| [`dbt-staging-sql`](./dbt-staging-sql.md) | A dbt staging SQL file. |
| [`avro`](./avro.md) | Avro schema. |
| [`avro-idl`](./avro-idl.md) | Avro IDL. |
| [`jsonschema`](./jsonschema.md) | JSON Schema. |
| [`pydantic-model`](./pydantic-model.md) | A Pydantic model. |
| [`protobuf`](./protobuf.md) | Protobuf schema. |
| [`odcs`](./odcs.md) | ODCS format. |
| [`rdf`](./rdf.md) | RDF representation. |
| [`html`](./html.md) | A standalone HTML page. |
| [`markdown`](./markdown.md) | Markdown documentation. |
| [`mermaid`](./mermaid.md) | A Mermaid diagram. |
| [`bigquery`](./bigquery.md) | BigQuery schema. |
| [`dbml`](./dbml.md) | DBML. |
| [`go`](./go.md) | Go structs. |
| [`spark`](./spark.md) | Spark `StructType` schema. |
| [`sqlalchemy`](./sqlalchemy.md) | SQLAlchemy models. |
| [`iceberg`](./iceberg.md) | Iceberg schema. |
| [`sodacl`](./sodacl.md) | SodaCL checks. |
| [`great-expectations`](./great-expectations.md) | Great Expectations suite. |
| [`data-caterer`](./data-caterer.md) | Data Caterer data-generation task. |
| [`dcs`](./dcs.md) | DCS format. |
| [`dqx`](./dqx.md) | Databricks DQX checks. |
| [`excel`](./excel.md) | ODCS Excel template. |
| [`custom`](./custom.md) | Any format, via a custom Jinja template. |

See the [`export` command reference](../commands/export.md) for the common signature.
