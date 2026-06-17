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

| Connection | `type` | Notes |
|---|---|---|
| [Amazon S3](./s3.md) | `s3` | CSV, JSON, Delta, Parquet on S3 / S3-compatible storage |
| [Google Cloud Storage](./gcs.md) | `s3` | Files on GCS via S3 interoperability |
| [Azure Blob / ADLS](./azure.md) | `azure` | Files on Azure Blob storage or ADLS Gen2 |
| [Amazon Athena](./athena.md) | `athena` | Athena over data in S3 |
| [Google BigQuery](./bigquery.md) | `bigquery` | BigQuery tables and views |
| [Microsoft SQL Server](./sqlserver.md) | `sqlserver` | SQL Server, Azure SQL, Synapse, Fabric |
| [Oracle](./oracle.md) | `oracle` | Oracle Database |
| [Databricks](./databricks.md) | `databricks` | Unity Catalog / Hive metastore (warehouse or notebook) |
| [Spark DataFrame](./dataframe.md) | `dataframe` | In-memory Spark DataFrames (programmatic) |
| [Snowflake](./snowflake.md) | `snowflake` | Snowflake |
| [Kafka](./kafka.md) | `kafka` | Kafka topics (experimental) |
| [Postgres](./postgres.md) | `postgres` | Postgres and Postgres-compatible (e.g. RisingWave) |
| [Amazon Redshift](./redshift.md) | `redshift` | Redshift (Postgres wire protocol) |
| [MySQL](./mysql.md) | `mysql` | MySQL / MariaDB |
| [Trino](./trino.md) | `trino` | Trino (basic, JWT, OAuth2) |
| [Apache Impala](./impala.md) | `impala` | Impala |
| [HTTP API](./api.md) | `api` | JSON HTTP APIs (GET only) |
| [Local files](./local.md) | `local` | Local Parquet, JSON, CSV, or Delta files |

:::tip
Missing a source? [Open an issue on GitHub](https://github.com/datacontract/datacontract-cli/issues).
:::

Each connection requires the matching [optional dependency (extra)](../quickstart.md#optional-dependencies-extras), or install everything with `datacontract-cli[all]`.
