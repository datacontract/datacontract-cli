---
sidebar_position: 0
title: "Test your Data"
slug: /testing
description: "Run schema and quality tests against your data source — Snowflake, BigQuery, Databricks, S3, Postgres, Kafka, and more."
---

# Test your Data

`datacontract test` connects to the data source defined in the contract's `servers` block and runs **schema** and **quality** tests to verify that the actual data complies with the data contract.

```bash
datacontract test --server production datacontract.yaml
```

## Supported connections

<div className="card-grid">
  <a className="doc-card" href="/testing/snowflake">
    <img src="/img/icons/snowflake.svg" alt="" />
    <span><span className="doc-card-title">Snowflake</span><span className="doc-card-desc">Import a contract from your tables and test in 5 minutes</span></span>
  </a>
  <a className="doc-card" href="/testing/bigquery">
    <img src="/img/icons/bigquery.svg" alt="" />
    <span><span className="doc-card-title">Google BigQuery</span><span className="doc-card-desc">Import a contract from your tables and test in 5 minutes</span></span>
  </a>
  <a className="doc-card" href="/testing/databricks">
    <img src="/img/icons/databricks.svg" alt="" />
    <span><span className="doc-card-title">Databricks</span><span className="doc-card-desc">Import a contract from Unity Catalog and test in 5 minutes</span></span>
  </a>
  <a className="doc-card" href="/testing/redshift">
    <img src="/img/icons/redshift.svg" alt="" />
    <span><span className="doc-card-title">Amazon Redshift</span><span className="doc-card-desc">Import a contract from your tables and test in 5 minutes</span></span>
  </a>
  <a className="doc-card" href="/testing/postgres">
    <img src="/img/icons/postgres.svg" alt="" />
    <span><span className="doc-card-title">Postgres</span><span className="doc-card-desc">Postgres and Postgres-compatible (e.g. RisingWave)</span></span>
  </a>
  <a className="doc-card" href="/testing/s3">
    <img src="/img/icons/s3.svg" alt="" />
    <span><span className="doc-card-title">Amazon S3</span><span className="doc-card-desc">CSV, JSON, Delta, Parquet on S3 / S3-compatible storage</span></span>
  </a>
  <a className="doc-card" href="/testing/local">
    <img src="/img/icons/local.svg" alt="" />
    <span><span className="doc-card-title">Local files</span><span className="doc-card-desc">Try it in 60 seconds — no credentials needed</span></span>
  </a>
  <a className="doc-card" href="/testing/athena">
    <img src="/img/icons/athena.svg" alt="" />
    <span><span className="doc-card-title">Amazon Athena</span><span className="doc-card-desc">Athena over data in S3</span></span>
  </a>
  <a className="doc-card" href="/testing/impala">
    <img src="/img/icons/impala.svg" alt="" />
    <span><span className="doc-card-title">Apache Impala</span><span className="doc-card-desc">Impala</span></span>
  </a>
  <a className="doc-card" href="/testing/azure">
    <img src="/img/icons/azure.svg" alt="" />
    <span><span className="doc-card-title">Azure Blob / ADLS</span><span className="doc-card-desc">Files on Azure Blob storage or ADLS Gen2</span></span>
  </a>
  <a className="doc-card" href="/testing/gcs">
    <img src="/img/icons/gcs.svg" alt="" />
    <span><span className="doc-card-title">Google Cloud Storage</span><span className="doc-card-desc">Files on GCS via S3 interoperability</span></span>
  </a>
  <a className="doc-card" href="/testing/api">
    <img src="/img/icons/api.svg" alt="" />
    <span><span className="doc-card-title">HTTP API</span><span className="doc-card-desc">JSON HTTP APIs (GET only)</span></span>
  </a>
  <a className="doc-card" href="/testing/kafka">
    <img src="/img/icons/kafka.svg" alt="" />
    <span><span className="doc-card-title">Kafka</span><span className="doc-card-desc">Kafka topics (experimental)</span></span>
  </a>
  <a className="doc-card" href="/testing/sqlserver">
    <img src="/img/icons/sqlserver.svg" alt="" />
    <span><span className="doc-card-title">Microsoft SQL Server</span><span className="doc-card-desc">SQL Server, Azure SQL, Synapse, Fabric</span></span>
  </a>
  <a className="doc-card" href="/testing/mysql">
    <img src="/img/icons/mysql.svg" alt="" />
    <span><span className="doc-card-title">MySQL</span><span className="doc-card-desc">MySQL / MariaDB</span></span>
  </a>
  <a className="doc-card" href="/testing/oracle">
    <img src="/img/icons/oracle.svg" alt="" />
    <span><span className="doc-card-title">Oracle</span><span className="doc-card-desc">Oracle Database</span></span>
  </a>
  <a className="doc-card" href="/testing/dataframe">
    <img src="/img/icons/spark.svg" alt="" />
    <span><span className="doc-card-title">Spark DataFrame</span><span className="doc-card-desc">In-memory Spark DataFrames (programmatic)</span></span>
  </a>
  <a className="doc-card" href="/testing/trino">
    <img src="/img/icons/trino.svg" alt="" />
    <span><span className="doc-card-title">Trino</span><span className="doc-card-desc">Trino (basic, JWT, OAuth2)</span></span>
  </a>
</div>

:::tip
Missing a source? [Open an issue on GitHub](https://github.com/datacontract/datacontract-cli/issues).
:::

Each connection requires the matching [optional dependency (extra)](../installation.md#optional-dependencies-extras), or install everything with `datacontract-cli[all]`.

## How it works

The CLI uses different engines based on the server `type`. Internally it connects with **DuckDB**, **Spark**, or a native connection, executes most checks with [_ibis_](https://ibis-project.org/) (compiling dialect-specific SQL per backend), and validates JSON with [_fastjsonschema_](https://pypi.org/project/fastjsonschema/).

Checks fall into categories you can select with `--checks`:

- `schema` — fields are present and have the expected type and nullability.
- `quality` — the [quality rules](../quality-rules/index.md) defined in the contract.
- `servicelevel` — service-level expectations (`slaProperties`).
- `custom` — custom checks.

Omit `--checks` to run all of them.

## Configuring the connection

The connection details (host, catalog, location, …) live in the contract's `servers` block; **credentials are provided as environment variables**.

```yaml
servers:
  - server: production
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

The page for each source above lists its `servers` fields and the environment variables it expects.

## Options

`--server`, `--schema-name`, and `--checks` narrow down what runs. `--output` with `--output-format` writes the results to a file as `json` or `junit`, `--publish` sends them to a URL, and `--include-failed-samples` collects a small sample of the offending rows. See the full [`test` command reference](../commands/test.md).

For CI/CD pipelines, use the [`ci`](../commands/ci.md) command, which wraps `test` with annotations, summaries, and exit-code control.

## Next steps

- Run the tests from Python instead of the CLI: **[Python Library](../python-library.md)**.
- Keep the tests running automatically: **[Scheduling and CI/CD](../ci-cd.md)**.
- Roll data contracts out across a team: **[Adopting Data Contracts](../best-practices.md)**.
