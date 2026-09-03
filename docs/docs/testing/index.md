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
  <a className="doc-card" href="/testing/duckdb">
    <img src="/img/icons/database.svg" alt="" />
    <span><span className="doc-card-title">DuckDB</span><span className="doc-card-desc">Tables inside a DuckDB database file</span></span>
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

Every other server `type` in ODCS, including the ones added in v3.2.0 (`hana`, `iceberg`, `exasol`, `teradata`, `ingres`, `vectorwise`, `versant`, `poet`), lints and exports, but `test` reports a warning that it cannot connect. `fastobjects` and `btrieve` are the ODCS synonyms of `poet` and `zen`, and `postgresql` of `postgres`.

## How it works

The CLI uses different engines based on the server `type`. Internally it connects with **DuckDB**, **Spark**, or a native connection, executes most checks with [_ibis_](https://ibis-project.org/) (compiling dialect-specific SQL per backend), and validates JSON with [_fastjsonschema_](https://pypi.org/project/fastjsonschema/).

Checks fall into categories you can select with `--checks`:

- `properties` — the [schema](../schema.md) attributes: presence, types, `required`, `unique`, primary keys, and `logicalTypeOptions`. `schema` is kept as a legacy alias. Not every ODCS attribute produces a check — see [What is not checked](../schema.md#what-is-not-checked) if one you declared appears to have no effect.
- `quality` — the [quality rules](../quality-rules/index.md) defined in the contract.
- `slaProperties` — the [service levels](../service-levels.md) defined in the contract. `servicelevel` is kept as a legacy alias.
- `custom` — custom checks.

Omit `--checks` to run all of them.

:::note
Selecting `properties` (or its legacy alias `schema`) is not metadata-only. The category says where a rule is defined in the contract, not how the check reads the database: constraints such as `required`, `unique`, enum, pattern, and ranges read column values and may scan data.

Use `--metadata-only` to skip these value-level checks: only the schema-reading checks (field presence and types) run, and the rest show as `skipped`. One exception: on JSON file and API sources, record validation still reads every record; `--metadata-only` does not disable it.
:::

`--dimension` cuts across those categories instead: it selects every check that measures one aspect of data quality — the [quality rules](../quality-rules/index.md#quality-dimensions) tagged with that `dimension` plus the schema and service level checks that measure the same thing.

`--quality-id` and `--tag` go the other way and narrow the run to individual [quality rules](../quality-rules/index.md#identifying-rules): `--quality-id` runs the one rule declaring that `id`, `--tag` runs every rule declaring that tag, and neither runs any schema or service level check.

## Dry Run

`--dry-run` reports the checks a run would execute and stops there. No data is read from the server, so every reported check has the result
`skipped` (or `warning` if they cannot be planned).

```bash
datacontract test datacontract.yaml --dry-run
```

A dry run needs no server credentials, which
makes it usable on a pull request build that has no warehouse access. A dry run
exits `0`: it is a plan, not a verdict.

:::note
A dry run is not offline in general: a contract that references [external semantics](../semantics.md) still fetches them. This is necessary to build all of its checks.
:::

:::caution
Contracts with `logicalType: blob` schemas on Azure do not support dry runs.
:::

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

Server fields may also hold `${VAR}` or `${VAR:-default}` references (ODCS v3.2.0), which `test` resolves from the environment when it connects; see [Variables in the data contract](../configuration.md#variables-in-the-data-contract).

The page for each source above lists its `servers` fields and the environment variables it expects. Credentials can also come from a YAML config file (`--config-file`), the Python `Config` class, or per-request API headers; see [Configuration](../configuration.md) for all mechanisms and their precedence.

## Options

`--server`, `--schema-name`, `--checks`, `--dimension`, `--quality-id`, and `--tag` narrow down what runs. `--output` with `--output-format` writes the results to a file as `json` or `junit`, `--publish` sends them to a URL, and `--include-failed-samples` collects a small sample of the offending rows. See the full [`test` command reference](../commands/test.md).

For CI/CD pipelines, use the [`ci`](../commands/ci.md) command, which wraps `test` with annotations, summaries, and exit-code control.

## Testing only a subset of rows

On large tables, a full scan for every test run is slow and expensive. `--filter` restricts the checks to the rows matching a SQL predicate, written in the dialect of the server:

```bash
# Test only the rows ingested in the last 24 hours
datacontract test datacontract.yaml --server production --filter "ingested_at >= CURRENT_TIMESTAMP - INTERVAL '24 hours'"

# Test a specific partition
datacontract test datacontract.yaml --server production --filter "batch_id = '2026-07-31'"
```

`--filter` requires that a single schema is tested. If the contract defines several schemas, either select one with `--schema-name` or pass `--filters` with a JSON object mapping schema name to predicate:

```bash
datacontract test datacontract.yaml --server production \
  --filters '{"orders": "ingested_at >= CURRENT_DATE - 1", "line_items": "ingested_at >= CURRENT_DATE - 1"}'
```

The predicate references the columns of the schema unqualified. It applies to all row-based checks: row counts, missing/invalid values, duplicates, freshness, retention, and failed-row samples. Schema checks (column presence and types) read metadata, not rows, so a filter does not change them. Custom SQL quality checks (`quality.type: sql`) and JSON schema validation of files run the query or file as-is and are not filtered.

The [API server](../api.md)'s `POST /test` accepts the same `filter` and `filters` as query parameters.

A filtered run only makes a statement about the tested subset. So the applied filters are recorded in the test results: the `Run` carries a `filters` field (per schema), the console output prints a `Row filter:` line, and the recorded SQL of each check contains the `WHERE` clause.

## Next steps

- Run the tests from Python instead of the CLI: **[Python Library](../python-library.md)**.
- Keep the tests running automatically: **[Scheduling](../scheduling/index.md)**.
- Roll data contracts out across a team: **[Adopting Data Contracts](../best-practices.md)**.
