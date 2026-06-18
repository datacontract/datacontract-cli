---
sidebar_position: 0
title: "Connect your Data"
slug: /connect
description: "Connect the Data Contract CLI to your data source — S3, BigQuery, Snowflake, Databricks, Postgres, Kafka, and more."
---

# Connect your Data

To [test](../testing.md) a data contract, the CLI connects to the data source defined in the contract's `servers` block. The connection details (host, catalog, location, …) live in the contract; **credentials are provided as environment variables**.

```yaml
servers:
  production:
    type: postgres   # selects the connection engine
    host: localhost
    port: 5432
    database: postgres
    schema: public
```

Environment variables are also loaded from a `.env` file in the current working directory (or the nearest parent directory containing one). Already-set environment variables take precedence over values from `.env`.

```bash
# .env
DATACONTRACT_POSTGRES_USERNAME=postgres
DATACONTRACT_POSTGRES_PASSWORD=postgres
```

## Supported connections

<div className="card-grid">
  <a className="doc-card" href="/connect/athena">
    <img src="/img/icons/athena.svg" alt="" />
    <span><span className="doc-card-title">Amazon Athena</span><span className="doc-card-desc">Athena over data in S3</span></span>
  </a>
  <a className="doc-card" href="/connect/redshift">
    <img src="/img/icons/redshift.svg" alt="" />
    <span><span className="doc-card-title">Amazon Redshift</span><span className="doc-card-desc">Redshift (Postgres wire protocol)</span></span>
  </a>
  <a className="doc-card" href="/connect/s3">
    <img src="/img/icons/s3.svg" alt="" />
    <span><span className="doc-card-title">Amazon S3</span><span className="doc-card-desc">CSV, JSON, Delta, Parquet on S3 / S3-compatible storage</span></span>
  </a>
  <a className="doc-card" href="/connect/impala">
    <img src="/img/icons/impala.svg" alt="" />
    <span><span className="doc-card-title">Apache Impala</span><span className="doc-card-desc">Impala</span></span>
  </a>
  <a className="doc-card" href="/connect/azure">
    <img src="/img/icons/azure.svg" alt="" />
    <span><span className="doc-card-title">Azure Blob / ADLS</span><span className="doc-card-desc">Files on Azure Blob storage or ADLS Gen2</span></span>
  </a>
  <a className="doc-card" href="/connect/databricks">
    <img src="/img/icons/databricks.svg" alt="" />
    <span><span className="doc-card-title">Databricks</span><span className="doc-card-desc">Unity Catalog / Hive metastore (warehouse or notebook)</span></span>
  </a>
  <a className="doc-card" href="/connect/bigquery">
    <img src="/img/icons/bigquery.svg" alt="" />
    <span><span className="doc-card-title">Google BigQuery</span><span className="doc-card-desc">BigQuery tables and views</span></span>
  </a>
  <a className="doc-card" href="/connect/gcs">
    <img src="/img/icons/gcs.svg" alt="" />
    <span><span className="doc-card-title">Google Cloud Storage</span><span className="doc-card-desc">Files on GCS via S3 interoperability</span></span>
  </a>
  <a className="doc-card" href="/connect/api">
    <img src="/img/icons/api.svg" alt="" />
    <span><span className="doc-card-title">HTTP API</span><span className="doc-card-desc">JSON HTTP APIs (GET only)</span></span>
  </a>
  <a className="doc-card" href="/connect/kafka">
    <img src="/img/icons/kafka.svg" alt="" />
    <span><span className="doc-card-title">Kafka</span><span className="doc-card-desc">Kafka topics (experimental)</span></span>
  </a>
  <a className="doc-card" href="/connect/local">
    <img src="/img/icons/local.svg" alt="" />
    <span><span className="doc-card-title">Local files</span><span className="doc-card-desc">Local Parquet, JSON, CSV, or Delta files</span></span>
  </a>
  <a className="doc-card" href="/connect/sqlserver">
    <img src="/img/icons/sqlserver.svg" alt="" />
    <span><span className="doc-card-title">Microsoft SQL Server</span><span className="doc-card-desc">SQL Server, Azure SQL, Synapse, Fabric</span></span>
  </a>
  <a className="doc-card" href="/connect/mysql">
    <img src="/img/icons/mysql.svg" alt="" />
    <span><span className="doc-card-title">MySQL</span><span className="doc-card-desc">MySQL / MariaDB</span></span>
  </a>
  <a className="doc-card" href="/connect/oracle">
    <img src="/img/icons/oracle.svg" alt="" />
    <span><span className="doc-card-title">Oracle</span><span className="doc-card-desc">Oracle Database</span></span>
  </a>
  <a className="doc-card" href="/connect/postgres">
    <img src="/img/icons/postgres.svg" alt="" />
    <span><span className="doc-card-title">Postgres</span><span className="doc-card-desc">Postgres and Postgres-compatible (e.g. RisingWave)</span></span>
  </a>
  <a className="doc-card" href="/connect/snowflake">
    <img src="/img/icons/snowflake.svg" alt="" />
    <span><span className="doc-card-title">Snowflake</span><span className="doc-card-desc">Snowflake</span></span>
  </a>
  <a className="doc-card" href="/connect/dataframe">
    <img src="/img/icons/spark.svg" alt="" />
    <span><span className="doc-card-title">Spark DataFrame</span><span className="doc-card-desc">In-memory Spark DataFrames (programmatic)</span></span>
  </a>
  <a className="doc-card" href="/connect/trino">
    <img src="/img/icons/trino.svg" alt="" />
    <span><span className="doc-card-title">Trino</span><span className="doc-card-desc">Trino (basic, JWT, OAuth2)</span></span>
  </a>
</div>

:::tip
Missing a source? [Open an issue on GitHub](https://github.com/datacontract/datacontract-cli/issues).
:::

Each connection requires the matching [optional dependency (extra)](../installation.md#optional-dependencies-extras), or install everything with `datacontract-cli[all]`.
