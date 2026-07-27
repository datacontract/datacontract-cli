---
sidebar_position: 5
title: "Test your contract"
description: "Connect to a data source and run schema and quality tests to verify a data contract, in development and on a schedule."
---

# Test your contract

`datacontract test` connects to a data source and runs **schema** and **quality** tests to verify that the actual data complies with the data contract.

```bash
datacontract test --server production datacontract.yaml
```

For CI/CD pipelines, use the [`ci`](./commands/ci.md) command, which wraps `test` with annotations, summaries, and exit-code control. See [Scheduling and CI/CD](#scheduling-and-cicd) below to run tests continuously.

## How it works

The CLI uses different engines based on the server `type`. Internally it connects with **DuckDB**, **Spark**, or a native connection, executes most checks with [_ibis_](https://ibis-project.org/) (compiling dialect-specific SQL per backend), and validates JSON with [_fastjsonschema_](https://pypi.org/project/fastjsonschema/).

Checks fall into categories you can select with `--checks`:

- `schema` — fields are present and have the expected type and nullability.
- `quality` — the [quality rules](./quality-rules/index.md) defined in the contract.
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

The CLI connects to object storage (S3, GCS, Azure), warehouses (BigQuery, Snowflake, Databricks, Redshift), databases (Postgres, MySQL, SQL Server, Oracle), query engines (Trino, Athena, Impala), Kafka, HTTP APIs, and local files.

See **[Connect your Data](./connect/index.md)** for the `servers` configuration and credentials for each source.

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

Data contracts deliver the most value when they are checked **continuously**: in CI/CD on every change, plus a recurring schedule (for example daily) so you catch data drift in production data over time.

The [`ci`](./commands/ci.md) command is purpose-built for this. Ready-made pipelines for GitHub Actions, Azure DevOps, cron with Docker, and orchestrators such as Airflow are on the **[Scheduling and CI/CD](./ci-cd.md)** page.

## Next steps

- Keep the tests running automatically: **[Scheduling and CI/CD](./ci-cd.md)**.
- Roll data contracts out across a team: **[Adopting Data Contracts](./best-practices.md)**.
