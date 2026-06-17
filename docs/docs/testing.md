---
sidebar_position: 5
title: "Data Contract Testing"
description: "Connect to a data source and run schema and quality tests to verify a data contract."
---

# Data Contract Testing

`datacontract test` connects to a data source and runs **schema** and **quality** tests to verify that the actual data complies with the data contract.

```bash
datacontract test --server production datacontract.yaml
```

For CI/CD pipelines, use the [`ci`](./commands/ci.md) command, which wraps `test` with annotations, summaries, and exit-code control.

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
