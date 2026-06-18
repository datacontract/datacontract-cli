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

## Example contract

The examples on each export page are generated from the same data contract, so you can compare formats side by side:

- [`examples/orders/orders.odcs.yaml`](https://github.com/datacontract/datacontract-cli/blob/main/examples/orders/orders.odcs.yaml) — an `orders` and `line_items` schema with a Snowflake and a BigQuery server. Used by most pages.
- [`examples/user_interactions/user_interactions.odcs.yaml`](https://github.com/datacontract/datacontract-cli/blob/main/examples/user_interactions/user_interactions.odcs.yaml) — a Databricks contract with DQX quality rules. Used by the [`dqx`](./dqx.md) page.

Download a file and run the commands below against it to reproduce the output.

## Available exporters

<div className="card-grid">
  <a className="doc-card" href="/exports/sql">
    <img src="/img/icons/database.svg" alt="" />
    <span><span className="doc-card-title">sql</span><span className="doc-card-desc">SQL DDL (CREATE TABLE).</span></span>
  </a>
  <a className="doc-card" href="/exports/sql-query">
    <img src="/img/icons/database.svg" alt="" />
    <span><span className="doc-card-title">sql-query</span><span className="doc-card-desc">A SQL SELECT query.</span></span>
  </a>
  <a className="doc-card" href="/exports/dbt-models">
    <img src="/img/icons/dbt.svg" alt="" />
    <span><span className="doc-card-title">dbt-models</span><span className="doc-card-desc">dbt model schema YAML.</span></span>
  </a>
  <a className="doc-card" href="/exports/dbt-sources">
    <img src="/img/icons/dbt.svg" alt="" />
    <span><span className="doc-card-title">dbt-sources</span><span className="doc-card-desc">dbt sources YAML.</span></span>
  </a>
  <a className="doc-card" href="/exports/dbt-staging-sql">
    <img src="/img/icons/dbt.svg" alt="" />
    <span><span className="doc-card-title">dbt-staging-sql</span><span className="doc-card-desc">A dbt staging SQL file.</span></span>
  </a>
  <a className="doc-card" href="/exports/avro">
    <img src="/img/icons/avro.svg" alt="" />
    <span><span className="doc-card-title">avro</span><span className="doc-card-desc">Avro schema.</span></span>
  </a>
  <a className="doc-card" href="/exports/avro-idl">
    <img src="/img/icons/avro.svg" alt="" />
    <span><span className="doc-card-title">avro-idl</span><span className="doc-card-desc">Avro IDL.</span></span>
  </a>
  <a className="doc-card" href="/exports/jsonschema">
    <img src="/img/icons/jsonschema.svg" alt="" />
    <span><span className="doc-card-title">jsonschema</span><span className="doc-card-desc">JSON Schema.</span></span>
  </a>
  <a className="doc-card" href="/exports/pydantic-model">
    <img src="/img/icons/pydantic.svg" alt="" />
    <span><span className="doc-card-title">pydantic-model</span><span className="doc-card-desc">A Pydantic model.</span></span>
  </a>
  <a className="doc-card" href="/exports/protobuf">
    <img src="/img/icons/generic.svg" alt="" />
    <span><span className="doc-card-title">protobuf</span><span className="doc-card-desc">Protobuf schema.</span></span>
  </a>
  <a className="doc-card" href="/exports/odcs">
    <img src="/img/icons/odcs.svg" alt="" />
    <span><span className="doc-card-title">odcs</span><span className="doc-card-desc">ODCS format.</span></span>
  </a>
  <a className="doc-card" href="/exports/rdf">
    <img src="/img/icons/rdf.svg" alt="" />
    <span><span className="doc-card-title">rdf</span><span className="doc-card-desc">RDF representation.</span></span>
  </a>
  <a className="doc-card" href="/exports/html">
    <img src="/img/icons/generic.svg" alt="" />
    <span><span className="doc-card-title">html</span><span className="doc-card-desc">A standalone HTML page.</span></span>
  </a>
  <a className="doc-card" href="/exports/markdown">
    <img src="/img/icons/markdown.svg" alt="" />
    <span><span className="doc-card-title">markdown</span><span className="doc-card-desc">Markdown documentation.</span></span>
  </a>
  <a className="doc-card" href="/exports/mermaid">
    <img src="/img/icons/mermaid.svg" alt="" />
    <span><span className="doc-card-title">mermaid</span><span className="doc-card-desc">A Mermaid diagram.</span></span>
  </a>
  <a className="doc-card" href="/exports/bigquery">
    <img src="/img/icons/bigquery.svg" alt="" />
    <span><span className="doc-card-title">bigquery</span><span className="doc-card-desc">BigQuery schema.</span></span>
  </a>
  <a className="doc-card" href="/exports/dbml">
    <img src="/img/icons/dbml.svg" alt="" />
    <span><span className="doc-card-title">dbml</span><span className="doc-card-desc">DBML.</span></span>
  </a>
  <a className="doc-card" href="/exports/go">
    <img src="/img/icons/go.svg" alt="" />
    <span><span className="doc-card-title">go</span><span className="doc-card-desc">Go structs.</span></span>
  </a>
  <a className="doc-card" href="/exports/spark">
    <img src="/img/icons/spark.svg" alt="" />
    <span><span className="doc-card-title">spark</span><span className="doc-card-desc">Spark StructType schema.</span></span>
  </a>
  <a className="doc-card" href="/exports/sqlalchemy">
    <img src="/img/icons/sqlalchemy.svg" alt="" />
    <span><span className="doc-card-title">sqlalchemy</span><span className="doc-card-desc">SQLAlchemy models.</span></span>
  </a>
  <a className="doc-card" href="/exports/iceberg">
    <img src="/img/icons/iceberg.svg" alt="" />
    <span><span className="doc-card-title">iceberg</span><span className="doc-card-desc">Iceberg schema.</span></span>
  </a>
  <a className="doc-card" href="/exports/sodacl">
    <img src="/img/icons/soda.svg" alt="" />
    <span><span className="doc-card-title">sodacl</span><span className="doc-card-desc">SodaCL checks.</span></span>
  </a>
  <a className="doc-card" href="/exports/great-expectations">
    <img src="/img/icons/great-expectations.svg" alt="" />
    <span><span className="doc-card-title">great-expectations</span><span className="doc-card-desc">Great Expectations suite.</span></span>
  </a>
  <a className="doc-card" href="/exports/data-caterer">
    <img src="/img/icons/data-caterer.svg" alt="" />
    <span><span className="doc-card-title">data-caterer</span><span className="doc-card-desc">Data Caterer data-generation task.</span></span>
  </a>
  <a className="doc-card" href="/exports/dcs">
    <img src="/img/icons/generic.svg" alt="" />
    <span><span className="doc-card-title">dcs</span><span className="doc-card-desc">DCS format.</span></span>
  </a>
  <a className="doc-card" href="/exports/dqx">
    <img src="/img/icons/dqx.svg" alt="" />
    <span><span className="doc-card-title">dqx</span><span className="doc-card-desc">Databricks DQX checks.</span></span>
  </a>
  <a className="doc-card" href="/exports/excel">
    <img src="/img/icons/excel.svg" alt="" />
    <span><span className="doc-card-title">excel</span><span className="doc-card-desc">ODCS Excel template.</span></span>
  </a>
  <a className="doc-card" href="/exports/custom">
    <img src="/img/icons/generic.svg" alt="" />
    <span><span className="doc-card-title">custom</span><span className="doc-card-desc">Any format, via a custom Jinja template.</span></span>
  </a>
</div>

See the [`export` command reference](../commands/export.md) for the common signature.
