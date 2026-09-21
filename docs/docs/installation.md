---
sidebar_position: 4
title: "Installation"
description: "Install the Data Contract CLI with uv, uvx, pip, pipx, or Docker, and choose the optional dependencies you need."
---

# Installation

Python 3.10–3.14 are supported. We recommend Python 3.11.

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

The image is also mirrored to Amazon ECR Public:

```bash
docker pull public.ecr.aws/s4e5k7s9/datacontract-cli
```

### Verifying the image

Released images are signed with [cosign](https://docs.sigstore.dev/cosign/signing/overview/) keyless signing, using the GitHub Actions OIDC identity of the release workflow. There is no public key to distribute — verification checks that the image was built and signed by that workflow, in this repository, from a release tag.

Install [cosign](https://docs.sigstore.dev/cosign/system_config/installation/) v2.6.3 or later (v3 or later recommended), then:

```bash
cosign verify datacontract/cli:latest \
  --certificate-identity-regexp '^https://github\.com/datacontract/datacontract-cli/\.github/workflows/release\.yaml@refs/tags/v' \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com
```

Both `--certificate-identity-regexp` and `--certificate-oidc-issuer` are required. Without them, `cosign verify` accepts any valid Sigstore signature — including one produced by someone else.

The same command works for the ECR mirror, which carries the signature and attestations along with the image:

```bash
cosign verify public.ecr.aws/s4e5k7s9/datacontract-cli:latest \
  --certificate-identity-regexp '^https://github\.com/datacontract/datacontract-cli/\.github/workflows/release\.yaml@refs/tags/v' \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com
```

Each image also ships an SBOM and SLSA provenance attestation, which you can inspect with:

```bash
docker buildx imagetools inspect datacontract/cli:latest --format '{{ json .SBOM }}'
docker buildx imagetools inspect datacontract/cli:latest --format '{{ json .Provenance }}'
```

Signatures are attached to images released after version 1.1.0. Older tags, 1.1.0 included, are unsigned.

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
| Databricks Runtime | `pip install datacontract-cli[databricks]` (also inside Databricks, using the cluster's own Spark session — see [Databricks Notebooks and Jobs](./databricks.md)) |
| DataFrame (Spark) | `pip install datacontract-cli[dataframe]` (PySpark not included — you supply the Spark session) |
| DBML | `pip install datacontract-cli[dbml]` |
| DuckDB (local file and API response testing) | `pip install datacontract-cli[duckdb]` |
| Excel | `pip install datacontract-cli[excel]` |
| GCS integration | `pip install datacontract-cli[gcs]` |
| Apache Iceberg (schema import and export, REST catalog testing) | `pip install datacontract-cli[iceberg]` |
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

Each [data source](./testing/index.md) lists the extra it needs.
