---
sidebar_position: 2
title: "Quickstart"
description: "Install the Data Contract CLI and test, export, and import your first data contract."
---

# Quickstart

This guide gets you from zero to a tested data contract in a few minutes.

## Install

The preferred way to install is [uv](https://docs.astral.sh/uv/):

```bash
uv tool install --python python3.11 --upgrade 'datacontract-cli[all]'
```

The `[all]` extra installs every optional data-source dependency. See [Installation options](#installation-options) below for `pip`, `pipx`, and Docker.

Verify the installation:

```bash
datacontract --version
```

## Test your first data contract

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

## Export to another format

You can use the contract metadata to generate downstream artifacts. For example, a SQL DDL:

```bash
datacontract export sql https://datacontract.com/orders-v1.odcs.yaml
```

```sql
-- Data Contract: orders
-- SQL Dialect: postgres
CREATE TABLE orders (
  order_id uuid not null primary key,
  customer_id text not null,
  order_total integer not null,
  order_timestamp timestamptz,
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

## Installation options

Python 3.10, 3.11, and 3.12 are supported. We recommend Python 3.11.

### uv (recommended)

```bash
uv tool install --python python3.11 --upgrade 'datacontract-cli[all]'
```

### uvx (run without installing)

```bash
uv run --with 'datacontract-cli[all]' datacontract --version
```

### pip

```bash
python3 -m pip install 'datacontract-cli[all]'
datacontract --version
```

### pip with venv

```bash
cd my-project
python3.11 -m venv venv
source venv/bin/activate
pip install 'datacontract-cli[all]'
datacontract --version
```

### pipx

```bash
pipx install 'datacontract-cli[all]'
datacontract --version
```

### Docker

```bash
docker pull datacontract/cli
docker run --rm -v "${PWD}:/home/datacontract" datacontract/cli
```

Create an alias to make it easier to use:

```bash
alias datacontract='docker run --rm -v "${PWD}:/home/datacontract" datacontract/cli:latest'
```

:::note
The output of Docker command line messages is limited to 80 columns and may include line breaks. Don't pipe Docker output to files if you want to export code — use the `--output` option instead.
:::

## Optional dependencies (extras)

The CLI defines several optional dependencies (extras) for specific server types. With `all`, every server dependency is included.

```bash
uv tool install --python python3.11 --upgrade 'datacontract-cli[all]'
```

Available extras:

| Dependency | Installation command |
|---|---|
| Amazon Athena | `pip install datacontract-cli[athena]` |
| Avro support | `pip install datacontract-cli[avro]` |
| Azure integration | `pip install datacontract-cli[azure]` |
| Google BigQuery | `pip install datacontract-cli[bigquery]` |
| CSV | `pip install datacontract-cli[csv]` |
| Databricks integration | `pip install datacontract-cli[databricks]` |
| DBML | `pip install datacontract-cli[dbml]` |
| DuckDB (local/S3/GCS/Azure file testing) | `pip install datacontract-cli[duckdb]` |
| Excel | `pip install datacontract-cli[excel]` |
| GCS integration | `pip install datacontract-cli[gcs]` |
| Iceberg | `pip install datacontract-cli[iceberg]` |
| Impala | `pip install datacontract-cli[impala]` |
| Kafka integration | `pip install datacontract-cli[kafka]` |
| MySQL integration | `pip install datacontract-cli[mysql]` |
| Oracle | `pip install datacontract-cli[oracle]` |
| Parquet | `pip install datacontract-cli[parquet]` |
| PostgreSQL integration | `pip install datacontract-cli[postgres]` |
| protobuf | `pip install datacontract-cli[protobuf]` |
| RDF | `pip install datacontract-cli[rdf]` |
| Amazon Redshift | `pip install datacontract-cli[redshift]` |
| S3 integration | `pip install datacontract-cli[s3]` |
| Snowflake integration | `pip install datacontract-cli[snowflake]` |
| Microsoft SQL Server | `pip install datacontract-cli[sqlserver]` |
| Trino | `pip install datacontract-cli[trino]` |
| API (run as web server) | `pip install datacontract-cli[api]` |
