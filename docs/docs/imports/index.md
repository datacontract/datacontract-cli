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

<div className="card-grid">
  <a className="doc-card" href="/imports/sql">
    <img src="/img/icons/database.svg" alt="" />
    <span><span className="doc-card-title">sql</span><span className="doc-card-desc">A SQL DDL file.</span></span>
  </a>
  <a className="doc-card" href="/imports/dbt">
    <img src="/img/icons/generic.svg" alt="" />
    <span><span className="doc-card-title">dbt</span><span className="doc-card-desc">A dbt manifest file.</span></span>
  </a>
  <a className="doc-card" href="/imports/avro">
    <img src="/img/icons/generic.svg" alt="" />
    <span><span className="doc-card-title">avro</span><span className="doc-card-desc">An Avro schema file.</span></span>
  </a>
  <a className="doc-card" href="/imports/dbml">
    <img src="/img/icons/database.svg" alt="" />
    <span><span className="doc-card-title">dbml</span><span className="doc-card-desc">A DBML file.</span></span>
  </a>
  <a className="doc-card" href="/imports/glue">
    <img src="/img/icons/glue.svg" alt="" />
    <span><span className="doc-card-title">glue</span><span className="doc-card-desc">AWS Glue Data Catalog.</span></span>
  </a>
  <a className="doc-card" href="/imports/bigquery">
    <img src="/img/icons/bigquery.svg" alt="" />
    <span><span className="doc-card-title">bigquery</span><span className="doc-card-desc">Google BigQuery (file or API).</span></span>
  </a>
  <a className="doc-card" href="/imports/unity">
    <img src="/img/icons/databricks.svg" alt="" />
    <span><span className="doc-card-title">unity</span><span className="doc-card-desc">Databricks Unity Catalog.</span></span>
  </a>
  <a className="doc-card" href="/imports/jsonschema">
    <img src="/img/icons/generic.svg" alt="" />
    <span><span className="doc-card-title">jsonschema</span><span className="doc-card-desc">A JSON Schema file.</span></span>
  </a>
  <a className="doc-card" href="/imports/json">
    <img src="/img/icons/generic.svg" alt="" />
    <span><span className="doc-card-title">json</span><span className="doc-card-desc">A JSON data file.</span></span>
  </a>
  <a className="doc-card" href="/imports/odcs">
    <img src="/img/icons/generic.svg" alt="" />
    <span><span className="doc-card-title">odcs</span><span className="doc-card-desc">An ODCS data contract file.</span></span>
  </a>
  <a className="doc-card" href="/imports/parquet">
    <img src="/img/icons/generic.svg" alt="" />
    <span><span className="doc-card-title">parquet</span><span className="doc-card-desc">A Parquet file.</span></span>
  </a>
  <a className="doc-card" href="/imports/csv">
    <img src="/img/icons/generic.svg" alt="" />
    <span><span className="doc-card-title">csv</span><span className="doc-card-desc">A CSV file.</span></span>
  </a>
  <a className="doc-card" href="/imports/protobuf">
    <img src="/img/icons/generic.svg" alt="" />
    <span><span className="doc-card-title">protobuf</span><span className="doc-card-desc">A Protobuf schema file.</span></span>
  </a>
  <a className="doc-card" href="/imports/spark">
    <img src="/img/icons/database.svg" alt="" />
    <span><span className="doc-card-title">spark</span><span className="doc-card-desc">A Spark schema / DataFrame.</span></span>
  </a>
  <a className="doc-card" href="/imports/iceberg">
    <img src="/img/icons/generic.svg" alt="" />
    <span><span className="doc-card-title">iceberg</span><span className="doc-card-desc">An Iceberg schema.</span></span>
  </a>
  <a className="doc-card" href="/imports/excel">
    <img src="/img/icons/generic.svg" alt="" />
    <span><span className="doc-card-title">excel</span><span className="doc-card-desc">An ODCS Excel template.</span></span>
  </a>
  <a className="doc-card" href="/imports/powerbi">
    <img src="/img/icons/generic.svg" alt="" />
    <span><span className="doc-card-title">powerbi</span><span className="doc-card-desc">A Power BI semantic model (.pbit, .bim, or .json).</span></span>
  </a>
  <a className="doc-card" href="/imports/snowflake">
    <img src="/img/icons/snowflake.svg" alt="" />
    <span><span className="doc-card-title">snowflake</span><span className="doc-card-desc">A Snowflake workspace.</span></span>
  </a>
</div>

See the [`import` command reference](../commands/import.md) for the common signature.
