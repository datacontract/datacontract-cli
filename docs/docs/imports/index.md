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

The [Snowflake](./snowflake.md), [BigQuery](./bigquery.md), [Amazon Redshift](./redshift.md), [Postgres](./postgres.md), [MySQL](./mysql.md), [SQL Server](./sqlserver.md), [Amazon Athena](./athena.md), [Amazon S3](./s3.md), [Google Cloud Storage](./gcs.md), [Azure Blob / ADLS](./adls.md), [Databricks](./databricks.md), and [AWS Glue](./glue.md) importers can connect directly to the live system and introspect your tables — no export files needed. Snowflake, BigQuery, Redshift, Postgres, MySQL, SQL Server, Athena, S3, GCS, ADLS, and Databricks also generate a ready-to-test `servers` block, so `datacontract test` works right after the import.

Run `datacontract import <format> --help` to see the format-specific options (e.g. `datacontract import sql --help`). If a format you need is missing, [open an issue on GitHub](https://github.com/datacontract/datacontract-cli/issues).

## Example sources

Each import page shows a runnable example: a small source file under [`examples/imports/`](https://github.com/datacontract/datacontract-cli/tree/main/examples/imports) and the data contract the CLI generates from it. Download a source and run the command on the page to reproduce the output.

## Available importers

<div className="card-grid">
  <a className="doc-card" href="/imports/adls">
    <img src="/img/icons/azure.svg" alt="" />
    <span><span className="doc-card-title">adls</span><span className="doc-card-desc">Files in Azure Blob Storage.</span></span>
  </a>
  <a className="doc-card" href="/imports/athena">
    <img src="/img/icons/athena.svg" alt="" />
    <span><span className="doc-card-title">athena</span><span className="doc-card-desc">An Amazon Athena database.</span></span>
  </a>
  <a className="doc-card" href="/imports/avro">
    <img src="/img/icons/avro.svg" alt="" />
    <span><span className="doc-card-title">avro</span><span className="doc-card-desc">An Avro schema file.</span></span>
  </a>
  <a className="doc-card" href="/imports/bigquery">
    <img src="/img/icons/bigquery.svg" alt="" />
    <span><span className="doc-card-title">bigquery</span><span className="doc-card-desc">Google BigQuery (file or API).</span></span>
  </a>
  <a className="doc-card" href="/imports/csv">
    <img src="/img/icons/custom.svg" alt="" />
    <span><span className="doc-card-title">csv</span><span className="doc-card-desc">A CSV file.</span></span>
  </a>
  <a className="doc-card" href="/imports/databricks">
    <img src="/img/icons/databricks.svg" alt="" />
    <span><span className="doc-card-title">databricks</span><span className="doc-card-desc">Databricks Unity Catalog.</span></span>
  </a>
  <a className="doc-card" href="/imports/dbml">
    <img src="/img/icons/dbml.svg" alt="" />
    <span><span className="doc-card-title">dbml</span><span className="doc-card-desc">A DBML file.</span></span>
  </a>
  <a className="doc-card" href="/imports/dbt">
    <img src="/img/icons/dbt.svg" alt="" />
    <span><span className="doc-card-title">dbt</span><span className="doc-card-desc">A dbt manifest file.</span></span>
  </a>
  <a className="doc-card" href="/imports/excel">
    <img src="/img/icons/excel.svg" alt="" />
    <span><span className="doc-card-title">excel</span><span className="doc-card-desc">An ODCS Excel template.</span></span>
  </a>
  <a className="doc-card" href="/imports/gcs">
    <img src="/img/icons/gcs.svg" alt="" />
    <span><span className="doc-card-title">gcs</span><span className="doc-card-desc">Files in Google Cloud Storage.</span></span>
  </a>
  <a className="doc-card" href="/imports/glue">
    <img src="/img/icons/glue.svg" alt="" />
    <span><span className="doc-card-title">glue</span><span className="doc-card-desc">AWS Glue Data Catalog.</span></span>
  </a>
  <a className="doc-card" href="/imports/iceberg">
    <img src="/img/icons/iceberg.svg" alt="" />
    <span><span className="doc-card-title">iceberg</span><span className="doc-card-desc">An Iceberg schema.</span></span>
  </a>
  <a className="doc-card" href="/imports/json">
    <img src="/img/icons/json.svg" alt="" />
    <span><span className="doc-card-title">json</span><span className="doc-card-desc">A JSON data file.</span></span>
  </a>
  <a className="doc-card" href="/imports/jsonschema">
    <img src="/img/icons/jsonschema.svg" alt="" />
    <span><span className="doc-card-title">jsonschema</span><span className="doc-card-desc">A JSON Schema file.</span></span>
  </a>
  <a className="doc-card" href="/imports/mysql">
    <img src="/img/icons/mysql.svg" alt="" />
    <span><span className="doc-card-title">mysql</span><span className="doc-card-desc">A MySQL database.</span></span>
  </a>
  <a className="doc-card" href="/imports/odcs">
    <img src="/img/icons/odcs.svg" alt="" />
    <span><span className="doc-card-title">odcs</span><span className="doc-card-desc">An ODCS data contract file.</span></span>
  </a>
  <a className="doc-card" href="/imports/parquet">
    <img src="/img/icons/parquet.svg" alt="" />
    <span><span className="doc-card-title">parquet</span><span className="doc-card-desc">A Parquet file.</span></span>
  </a>
  <a className="doc-card" href="/imports/postgres">
    <img src="/img/icons/postgres.svg" alt="" />
    <span><span className="doc-card-title">postgres</span><span className="doc-card-desc">A Postgres schema.</span></span>
  </a>
  <a className="doc-card" href="/imports/powerbi">
    <img src="/img/icons/powerbi.svg" alt="" />
    <span><span className="doc-card-title">powerbi</span><span className="doc-card-desc">A Power BI semantic model (.pbit, .bim, or .json).</span></span>
  </a>
  <a className="doc-card" href="/imports/protobuf">
    <img src="/img/icons/custom.svg" alt="" />
    <span><span className="doc-card-title">protobuf</span><span className="doc-card-desc">A Protobuf schema file.</span></span>
  </a>
  <a className="doc-card" href="/imports/redshift">
    <img src="/img/icons/redshift.svg" alt="" />
    <span><span className="doc-card-title">redshift</span><span className="doc-card-desc">An Amazon Redshift schema.</span></span>
  </a>
  <a className="doc-card" href="/imports/s3">
    <img src="/img/icons/s3.svg" alt="" />
    <span><span className="doc-card-title">s3</span><span className="doc-card-desc">Files in an Amazon S3 bucket.</span></span>
  </a>
  <a className="doc-card" href="/imports/snowflake">
    <img src="/img/icons/snowflake.svg" alt="" />
    <span><span className="doc-card-title">snowflake</span><span className="doc-card-desc">A Snowflake workspace.</span></span>
  </a>
  <a className="doc-card" href="/imports/spark">
    <img src="/img/icons/spark.svg" alt="" />
    <span><span className="doc-card-title">spark</span><span className="doc-card-desc">A Spark schema / DataFrame.</span></span>
  </a>
  <a className="doc-card" href="/imports/sql">
    <img src="/img/icons/database.svg" alt="" />
    <span><span className="doc-card-title">sql</span><span className="doc-card-desc">A SQL DDL file.</span></span>
  </a>
  <a className="doc-card" href="/imports/sqlserver">
    <img src="/img/icons/sqlserver.svg" alt="" />
    <span><span className="doc-card-title">sqlserver</span><span className="doc-card-desc">A SQL Server database.</span></span>
  </a>
</div>

See the [`import` command reference](../commands/import.md) for the common signature.
