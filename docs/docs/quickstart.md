---
sidebar_position: 2
title: "Quickstart"
description: "Install the Data Contract CLI and test, export, and import your first data contract."
---

# Quickstart

This guide gets you from zero to a tested data contract in a few minutes — first against a hosted demo database (60 seconds, nothing to set up), then against your own data warehouse (about 5 minutes).

## Install

The preferred way to install is [uv](https://docs.astral.sh/uv/). Add the extra for the data source you want to test — the demo below uses Postgres:

```bash
uv tool install --python python3.11 --upgrade 'datacontract-cli[postgres]'
```

Every source has its own extra (`snowflake`, `bigquery`, `databricks`, `s3`, `duckdb` for local files, …), so you only install what you need. `datacontract-cli[all]` pulls in every optional dependency, including Spark — convenient, but a much larger download. See [Installation options](#installation-options) below for `pip`, `pipx`, and Docker.

Verify the installation:

```bash
datacontract --version
```

## Test your first data contract (60 seconds)

Let's use the example contract published at
[`https://datacontract.com/orders-v1.odcs.yaml`](https://datacontract.com/orders-v1.odcs.yaml).
It contains a `servers` section pointing at a Postgres database, a `schema`, and `quality` attributes.

Provide credentials as environment variables and run `test`:

```bash
export DATACONTRACT_POSTGRES_USERNAME=datacontract_cli.egzhawjonpfweuutedfy
export DATACONTRACT_POSTGRES_PASSWORD=jio10JuQfDfl9JCCPdaCCpuZ1YO

datacontract test https://datacontract.com/orders-v1.odcs.yaml
```

```
Testing https://datacontract.com/orders-v1.odcs.yaml
Server: production (type=postgres, host=..., database=postgres, schema=dp_orders_v1)
╭────────┬──────────────────────────────────────────────────────────┬─────────────────────────┬─────────╮
│ Result │ Check                                                      │ Field                   │ Details │
├────────┼──────────────────────────────────────────────────────────┼─────────────────────────┼─────────┤
│ passed │ Check that field 'order_id' is present                     │ orders.order_id         │         │
│ passed │ Check that field order_id has type UUID                    │ orders.order_id         │         │
│ passed │ Check that unique field order_id has no duplicate values   │ orders.order_id         │         │
│  ...   │                                                            │                         │         │
╰────────┴──────────────────────────────────────────────────────────┴─────────────────────────┴─────────╯
🟢 data contract is valid. Run 25 checks. Took 3.938887 seconds.
```

The CLI verified that the YAML itself is valid, that all records comply with the schema, and that all quality attributes are met.

## Test your own data (5 minutes)

The real magic moment is when a contract catches drift in *your* data. Import a contract straight from an existing table — the import generates the schema and a ready-to-test `servers` block — then test the actual data against it:

```bash
datacontract import snowflake --source <account> --database ORDER_DB --schema PUBLIC --output datacontract.yaml
datacontract test datacontract.yaml
```

Follow the copy-paste guide for your data source, including credentials setup and troubleshooting:

- **[Snowflake](./testing/snowflake.md)** — import from your tables, test in 5 minutes
- **[Google BigQuery](./testing/bigquery.md)** — import from your tables, test in 5 minutes
- **[Databricks](./testing/databricks.md)** — import from Unity Catalog, test in 5 minutes
- **[Amazon Redshift](./testing/redshift.md)** — import from your tables, test in 5 minutes
- **[Postgres](./testing/postgres.md)**, **[Amazon S3](./testing/s3.md)**, and [15+ other sources](./testing/index.md)
- **[Local files](./testing/local.md)** — no warehouse or credentials needed, works offline

Each guide ends with the same payoff: tighten an expectation, rerun `datacontract test`, and watch the contract catch the violation with exit code `1` — the exact behavior you'll later use [in CI/CD](./ci-cd.md).

## Export to another format

You can use the contract metadata to generate downstream artifacts. For example, a SQL DDL:

```bash
datacontract export sql https://datacontract.com/orders-v1.odcs.yaml
```

```sql
-- Data Contract: orders
-- SQL Dialect: postgres
CREATE TABLE orders (
  order_id UUID not null primary key,
  customer_id text not null,
  order_total integer not null,
  order_timestamp TIMESTAMPTZ,
  order_status text
);
```

Or an HTML page:

```bash
datacontract export html --output orders-v1.odcs.html https://datacontract.com/orders-v1.odcs.yaml
```

See **[Exports](./exports/index.md)** for all 25+ target formats.

## The typical workflow

```bash
# Create a new data contract from a template and write it to odcs.yaml
datacontract init odcs.yaml

# Edit the data contract in the Data Contract Editor (web UI)
datacontract edit odcs.yaml

# Lint the odcs.yaml and stop after the first validation error (default)
datacontract lint odcs.yaml

# Show a changelog between two data contracts
datacontract changelog v1.odcs.yaml v2.odcs.yaml

# Execute schema and quality checks (credentials via environment variables)
datacontract test odcs.yaml

# Generate dbt tests from a contract into your dbt project and run `dbt test`
datacontract dbt sync orders.odcs.yaml --project-dir ./warehouse

# Export to HTML (and many other formats)
datacontract export html odcs.yaml --output odcs.html

# Import from an existing SQL DDL
datacontract import sql --source my-ddl.sql --dialect postgres --output odcs.yaml
```

## Use it as a Python library

```python
from datacontract.data_contract import DataContract

data_contract = DataContract(data_contract_file="odcs.yaml")
run = data_contract.test()
if not run.has_passed():
    print("Data quality validation failed.")
    # Abort pipeline, alert, or take corrective actions...
```

## Next steps

- Keep the tests running automatically: **[Scheduling and CI/CD](./ci-cd.md)** — GitHub Actions, Azure DevOps, cron, and orchestrators.
- Roll data contracts out across a team: **[Adopting Data Contracts](./best-practices.md)**.
- Browse everything the CLI can do: **[Commands](./commands/index.md)**.

## Installation options

See the dedicated **[Installation](./installation.md)** page for all options (uv, uvx, pip, venv, pipx, Docker) and the full list of optional dependencies (extras).
