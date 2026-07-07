---
sidebar_position: 4
title: "Installation"
description: "Install the Data Contract CLI with uv, uvx, pip, pipx, or Docker, and choose the optional dependencies you need."
---

# Installation

Python 3.10, 3.11, and 3.12 are supported. We recommend Python 3.11.

The `[all]` extra installs every optional data-source dependency. To keep the install small, replace it with just the [extras](#optional-dependencies-extras) you need.

## uv (recommended)

The preferred way to install is [uv](https://docs.astral.sh/uv/):

```bash
uv tool install --python python3.11 --upgrade 'datacontract-cli[all]'
datacontract --version
```

## uvx (run without installing)

If you have [uv](https://docs.astral.sh/uv/) installed, you can run the CLI directly without installing it:

```bash
uv run --with 'datacontract-cli[all]' datacontract --version
```

## pip

```bash
python3 -m pip install 'datacontract-cli[all]'
datacontract --version
```

## pip with venv

Typically it's better to install into a virtual environment for your project:

```bash
cd my-project
python3.11 -m venv venv
source venv/bin/activate
pip install 'datacontract-cli[all]'
datacontract --version
```

## pipx

`pipx` installs into an isolated environment:

```bash
pipx install 'datacontract-cli[all]'
datacontract --version
```

## Docker

Use the Docker image to run the CLI without a local Python install — convenient for CI/CD:

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

Each [data source](./connect/index.md) lists the extra it needs.
