---
sidebar_position: 4
title: "Testing"
description: "Connect to a data source and run schema and quality tests to verify a data contract, in development and on a schedule."
---

# Testing

`datacontract test` connects to a data source and runs **schema** and **quality** tests to verify that the actual data complies with the data contract.

```bash
datacontract test --server production datacontract.yaml
```

For CI/CD pipelines, use the [`ci`](./commands/ci.md) command, which wraps `test` with annotations, summaries, and exit-code control. See [Scheduling and CI/CD](#scheduling-and-cicd) below to run tests continuously.

## How it works

The CLI uses different engines based on the server `type`. Internally it connects with **DuckDB**, **Spark**, or a native connection, executes most checks with [_ibis_](https://ibis-project.org/) (compiling dialect-specific SQL per backend), and validates JSON with [_fastjsonschema_](https://pypi.org/project/fastjsonschema/).

Checks fall into categories you can select with `--checks`:

- `schema` — fields are present and have the expected type and nullability.
- `quality` — the [quality rules](./quality-rules.md) defined in the contract.
- `servicelevel` — service-level expectations (`slaProperties`).
- `custom` — custom checks.

Omit `--checks` to run all of them.

## Connecting to a data source

The `servers` block in the `datacontract.yaml` is used to set up the connection. Credentials such as usernames and passwords are provided as **environment variables**.

Environment variables are also loaded from a `.env` file in the current working directory (or the nearest parent directory containing one, so you can run the CLI from a subfolder of your project). Already-set environment variables take precedence over values from the `.env` file.

```bash
# .env
DATACONTRACT_POSTGRES_USERNAME=postgres
DATACONTRACT_POSTGRES_PASSWORD=postgres
```

## Supported data sources

| Server `type` | Notes | Required extra |
|---|---|---|
| `s3` | JSON, CSV, Parquet, Delta on Amazon S3 / S3-compatible storage | `s3` / `duckdb` |
| `gcs` | Google Cloud Storage files | `gcs` / `duckdb` |
| `azure` | Azure Blob / ADLS files | `azure` / `duckdb` |
| `athena` | Amazon Athena | `athena` |
| `bigquery` | Google BigQuery | `bigquery` |
| `sqlserver` | Microsoft SQL Server | `sqlserver` |
| `oracle` | Oracle | `oracle` |
| `databricks` | Databricks (SQL warehouse, also programmatic via Spark) | `databricks` |
| `dataframe` | An in-memory Spark DataFrame (programmatic) | — |
| `snowflake` | Snowflake | `snowflake` |
| `kafka` | Kafka topics (Avro/JSON) | `kafka` |
| `postgres` | Postgres and Postgres-compatible (e.g. RisingWave) | `postgres` |
| `redshift` | Amazon Redshift (over the Postgres wire protocol) | `redshift` |
| `mysql` | MySQL / MariaDB | `mysql` |
| `trino` | Trino (basic, JWT, or OAuth2 auth) | `trino` |
| `impala` | Apache Impala | `impala` |
| `api` | JSON HTTP APIs (GET only) | — |
| `local` | Local files in Parquet, JSON, CSV, or Delta | `duckdb` |

:::tip
Missing a source? [Open an issue on GitHub](https://github.com/datacontract/datacontract-cli/issues).
:::

## Examples

### Postgres

```yaml
servers:
  postgres:
    type: postgres
    host: localhost
    port: 5432
    database: postgres
    schema: public
models:
  my_table_1:
    type: table
    fields:
      my_column_1:
        type: varchar
```

| Environment variable | Example | Description |
|---|---|---|
| `DATACONTRACT_POSTGRES_USERNAME` | `postgres` | Username |
| `DATACONTRACT_POSTGRES_PASSWORD` | `mysecretpassword` | Password |

### Snowflake

```yaml
servers:
  snowflake:
    type: snowflake
    account: my-account
    database: my_database
    schema: my_schema
```

Credentials are provided via `DATACONTRACT_SNOWFLAKE_USERNAME`, `DATACONTRACT_SNOWFLAKE_PASSWORD`, `DATACONTRACT_SNOWFLAKE_WAREHOUSE`, and `DATACONTRACT_SNOWFLAKE_ROLE`.

### Local files

```yaml
servers:
  local:
    type: local
    path: ./*.parquet
    format: parquet
models:
  my_table_1:
    type: table
    fields:
      my_column_1:
        type: varchar
```

### Trino

```yaml
servers:
  trino:
    type: trino
    host: localhost
    port: 8080
    catalog: my_catalog
    schema: my_schema
models:
  my_table_1:
    type: table
    fields:
      my_column_2:
        type: object
        config:
          trinoType: row(en_us varchar, pt_br varchar)
```

| Environment variable | Description |
|---|---|
| `DATACONTRACT_TRINO_USERNAME` | Username for `basic` auth |
| `DATACONTRACT_TRINO_PASSWORD` | Password for `basic` auth |
| `DATACONTRACT_TRINO_AUTHENTICATION` | `basic` (default), `jwt`, or `oauth2` |
| `DATACONTRACT_TRINO_JWT_TOKEN` | JWT bearer token for `jwt` auth |

### JSON HTTP API

```yaml
servers:
  api:
    type: "api"
    location: "https://api.example.com/path"
    delimiter: none # new_line, array, or none (default)
models:
  my_object:
    type: object
    fields:
      field1:
        type: string
```

Set the optional `DATACONTRACT_API_HEADER_AUTHORIZATION` environment variable (e.g. a `Bearer` token) for authenticated APIs.

:::note
The full set of environment variables for every server type — including S3, GCS, Azure, Athena, BigQuery, SQL Server, Oracle, Databricks, Redshift, MySQL, Kafka, and Impala — is documented in the project [README](https://github.com/datacontract/datacontract-cli#supported-data-sources).
:::

## Useful options

| Option | Description |
|---|---|
| `--server` | Which server to test (the key in the `servers` block), or `all` (default). |
| `--schema-name` | Which schema/model to test, or `all` (default). |
| `--checks` | Comma-separated categories: `schema`, `quality`, `servicelevel`, `custom`. |
| `--output` + `--output-format` | Write results to a file as `json` or `junit`. |
| `--publish` | URL to publish the results to after the test. |
| `--include-failed-samples` | Collect a small sample of rows that failed each check (identifiers + offending columns; off by default). |
| `--logs` | Print logs. |

See the full [`test` command reference](./commands/test.md).

## Programmatic use

```python
from datacontract.data_contract import DataContract

data_contract = DataContract(data_contract_file="odcs.yaml")
run = data_contract.test()
if not run.has_passed():
    print("Data quality validation failed.")
```

## Scheduling and CI/CD

Data contracts deliver the most value when they are checked **continuously**, not just once. The recommended practice is to test contracts in CI/CD on every change and, in addition, to run them on a recurring schedule (for example daily) so you detect data drift and quality regressions in production data over time.

The [`ci`](./commands/ci.md) command is purpose-built for this: it wraps `test` with CI-friendly annotations, a markdown summary, machine-readable output, and exit-code control via `--fail-on`.

### GitHub Actions (on change and scheduled)

```yaml
# .github/workflows/datacontract.yml
name: Data Contract CI

on:
  push:
    branches: [main]
  pull_request:
  schedule:
    # Run every day at 06:00 UTC to catch data drift in production
    - cron: "0 6 * * *"

jobs:
  datacontract-ci:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install datacontract-cli
      # Test one or more data contracts (supports globs, e.g. contracts/*.yaml)
      - run: datacontract ci datacontract.yaml
        env:
          DATACONTRACT_POSTGRES_USERNAME: ${{ secrets.DB_USERNAME }}
          DATACONTRACT_POSTGRES_PASSWORD: ${{ secrets.DB_PASSWORD }}
```

There is also a ready-made GitHub Action — see [datacontract/datacontract-action](https://github.com/datacontract/datacontract-action/).

### Azure DevOps

```yaml
# azure-pipelines.yml
trigger:
  branches:
    include:
      - main

schedules:
  - cron: "0 6 * * *"
    displayName: Daily data contract tests
    branches:
      include: [main]
    always: true

pool:
  vmImage: "ubuntu-latest"

steps:
  - task: UsePythonVersion@0
    inputs:
      versionSpec: "3.11"
  - script: pip install datacontract-cli
    displayName: "Install datacontract-cli"
  - script: datacontract ci datacontract.yaml
    displayName: "Run data contract tests"
```

### Plain cron with Docker

If you don't have a CI system, schedule the Docker image with cron:

```cron
# Run every day at 06:00 — /etc/crontab or `crontab -e`
0 6 * * *  docker run --rm -v "/path/to/contracts:/home/datacontract" \
  -e DATACONTRACT_POSTGRES_USERNAME -e DATACONTRACT_POSTGRES_PASSWORD \
  datacontract/cli:latest ci datacontract.yaml
```

### Orchestrators (Airflow, Databricks, …)

Because the CLI is also a Python library, you can call it from any orchestrator task:

```python
from datacontract.data_contract import DataContract

def test_orders_contract():
    run = DataContract(data_contract_file="orders.odcs.yaml").test()
    if not run.has_passed():
        raise RuntimeError("Data contract tests failed")
```

Wrap this in an Airflow `PythonOperator`, a Databricks job, a Dagster op, or a Prefect task and schedule it with your orchestrator's native scheduler.

### Publishing scheduled results

To track results over time, publish each run to an Entropy Data instance:

```bash
datacontract ci datacontract.yaml --publish https://api.entropy-data.com/api/test-results
```

### Controlling failure behavior

Use `--fail-on` to decide when a scheduled run should be marked as failed:

```bash
# Fail the job on errors only (default)
datacontract ci --fail-on error datacontract.yaml

# Also fail on warnings
datacontract ci --fail-on warning datacontract.yaml

# Never fail (e.g. report-only schedules)
datacontract ci --fail-on never datacontract.yaml
```
