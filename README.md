# Data Contract CLI

<p>
  <a href="https://github.com/datacontract/datacontract-cli/actions/workflows/ci.yaml?query=branch%3Amain">
    <img alt="Test Workflow" src="https://img.shields.io/github/actions/workflow/status/datacontract/datacontract-cli/ci.yaml?branch=main"></a>
  <a href="https://pypi.org/project/datacontract-cli/">
    <img alt="PyPI Version" src="https://img.shields.io/pypi/v/datacontract-cli" /></a>
  <a href="https://github.com/datacontract/datacontract-cli">
    <img alt="Stars" src="https://img.shields.io/github/stars/datacontract/datacontract-cli" /></a>
  <a href="https://datacontract.com/slack" rel="nofollow"><img src="https://img.shields.io/badge/slack-join_chat-white.svg?logo=slack&amp;style=social" alt="Slack Status" data-canonical-src="https://img.shields.io/badge/slack-join_chat-white.svg?logo=slack&amp;style=social" style="max-width: 100%;"></a>
</p>

The `datacontract` CLI is an open-source command-line tool for working with [data contracts](https://datacontract.com).
It natively supports the [Open Data Contract Standard](https://bitol-io.github.io/open-data-contract-standard/latest/) to lint data contracts, connect to data sources and execute schema and quality tests, and export to different formats. 
The tool is written in Python. 
It can be used as a standalone CLI tool, in a CI/CD pipeline, or directly as a Python library.

![Main features of the Data Contract CLI](datacontractcli.png)

> 📖 **Full documentation: [docs.datacontract.com](https://docs.datacontract.com)**
>
> Quick links: [Quickstart](https://docs.datacontract.com/quickstart) · [Commands](https://docs.datacontract.com/commands) · [Best Practices](https://docs.datacontract.com/best-practices) · [Custom Export and Import](https://docs.datacontract.com/extending) · [Development Setup](#development-setup)

## Getting started

Let's look at this data contract:
[https://datacontract.com/orders-v1.odcs.yaml](https://datacontract.com/orders-v1.odcs.yaml)

We have a _servers_ section with endpoint details to a Postgres database, _schema_ for the structure and semantics of the data, _service levels_ and _quality_ attributes that describe the expected freshness and number of rows.

This data contract contains all information to connect to the database and check that the actual data meets the defined schema specification and quality expectations.
We can use this information to test if the actual data product is compliant to the data contract.

Let's use [uv](https://docs.astral.sh/uv/) to install the CLI (or use the [Docker image](#docker)),
```bash
$ uv tool install --python python3.11 --upgrade 'datacontract-cli[all]'
```


Now, let's run the tests:

```bash
$ export DATACONTRACT_POSTGRES_USERNAME=datacontract_cli.egzhawjonpfweuutedfy
$ export DATACONTRACT_POSTGRES_PASSWORD=jio10JuQfDfl9JCCPdaCCpuZ1YO
$ datacontract test https://datacontract.com/orders-v1.odcs.yaml

# returns:
Testing https://datacontract.com/orders-v1.odcs.yaml
Server: production (type=postgres, host=aws-1-eu-central-2.pooler.supabase.com, port=6543, database=postgres, schema=dp_orders_v1)
╭────────┬──────────────────────────────────────────────────────────┬─────────────────────────┬─────────╮
│ Result │ Check                                                    │ Field                   │ Details │
├────────┼──────────────────────────────────────────────────────────┼─────────────────────────┼─────────┤
│ passed │ Check that field 'line_item_id' is present               │ line_items.line_item_id │         │
│ passed │ Check that field line_item_id has type UUID              │ line_items.line_item_id │         │
│ passed │ Check that field line_item_id has no missing values      │ line_items.line_item_id │         │
│ passed │ Check that field 'order_id' is present                   │ line_items.order_id     │         │
│ passed │ Check that field order_id has type UUID                  │ line_items.order_id     │         │
│ passed │ Check that field 'price' is present                      │ line_items.price        │         │
│ passed │ Check that field price has type INTEGER                  │ line_items.price        │         │
│ passed │ Check that field price has no missing values             │ line_items.price        │         │
│ passed │ Check that field 'sku' is present                        │ line_items.sku          │         │
│ passed │ Check that field sku has type TEXT                       │ line_items.sku          │         │
│ passed │ Check that field sku has no missing values               │ line_items.sku          │         │
│ passed │ Check that field 'customer_id' is present                │ orders.customer_id      │         │
│ passed │ Check that field customer_id has type TEXT               │ orders.customer_id      │         │
│ passed │ Check that field customer_id has no missing values       │ orders.customer_id      │         │
│ passed │ Check that field 'order_id' is present                   │ orders.order_id         │         │
│ passed │ Check that field order_id has type UUID                  │ orders.order_id         │         │
│ passed │ Check that field order_id has no missing values          │ orders.order_id         │         │
│ passed │ Check that unique field order_id has no duplicate values │ orders.order_id         │         │
│ passed │ Check that field 'order_status' is present               │ orders.order_status     │         │
│ passed │ Check that field order_status has type TEXT              │ orders.order_status     │         │
│ passed │ Check that field 'order_timestamp' is present            │ orders.order_timestamp  │         │
│ passed │ Check that field order_timestamp has type TIMESTAMPTZ    │ orders.order_timestamp  │         │
│ passed │ Check that field 'order_total' is present                │ orders.order_total      │         │
│ passed │ Check that field order_total has type INTEGER            │ orders.order_total      │         │
│ passed │ Check that field order_total has no missing values       │ orders.order_total      │         │
╰────────┴──────────────────────────────────────────────────────────┴─────────────────────────┴─────────╯
🟢 data contract is valid. Run 25 checks. Took 3.938887 seconds.
```

Voilà, the CLI tested that the YAML itself is valid, all records comply with the schema, and all quality attributes are met.

We can also use the data contract metadata to export in many [formats](https://docs.datacontract.com/exports), e.g., to generate a SQL DDL:

```bash
$ datacontract export sql https://datacontract.com/orders-v1.odcs.yaml

# returns:
-- Data Contract: orders
-- SQL Dialect: postgres
CREATE TABLE orders (
  order_id None not null primary key,
  customer_id text not null,
  order_total integer not null,
  order_timestamp None,
  order_status text
);
CREATE TABLE line_items (
  line_item_id None not null primary key,
  sku text not null,
  price integer not null,
  order_id None
);
```

Or generate an HTML export:

```bash
$ datacontract export html --output orders-v1.odcs.html https://datacontract.com/orders-v1.odcs.yaml
```

[//]: # (which will create this [HTML export]&#40;https://datacontract.com/examples/orders-latest/datacontract.html&#41;.)


## Usage

```bash
# create a new data contract from example and write it to odcs.yaml
$ datacontract init odcs.yaml

# edit the data contract in the Data Contract Editor (web UI)
$ datacontract edit odcs.yaml

# lint the odcs.yaml and stop after the first validation error (default).
$ datacontract lint odcs.yaml

# show a changelog between two data contracts
$ datacontract changelog v1.odcs.yaml v2.odcs.yaml

# execute schema and quality checks (define credentials as environment variables)
$ datacontract test odcs.yaml

# generate dbt tests from a contract into your dbt project and run `dbt test`
$ datacontract dbt sync orders.odcs.yaml --project-dir ./warehouse

# export data contract as html (other formats: avro, dbt-models, dbt-sources, dbt-staging-sql, jsonschema, odcs, rdf, sql, sodacl, terraform, ...)
$ datacontract export html datacontract.yaml --output odcs.html

# import sql (other formats: avro, glue, bigquery, jsonschema, excel ...)
$ datacontract import sql --source my-ddl.sql --dialect postgres --output odcs.yaml

# import from Excel template
$ datacontract import excel --source odcs.xlsx --output odcs.yaml

# export to Excel template  
$ datacontract export excel --output odcs.xlsx odcs.yaml
```

## Programmatic (Python)
```python
from datacontract.data_contract import DataContract

data_contract = DataContract(data_contract_file="odcs.yaml")
run = data_contract.test()
if not run.has_passed():
    print("Data quality validation failed.")
    # Abort pipeline, alert, or take corrective actions...
```

## How to

- [How to integrate Data Contract CLI in your CI/CD pipeline as a GitHub Action](https://github.com/datacontract/datacontract-action/)
- [How to run the Data Contract CLI API to test data contracts with POST requests](https://cli.datacontract.com/API)
- [How to run Data Contract CLI in a Databricks pipeline](https://www.datamesh-architecture.com/howto/build-a-dataproduct-with-databricks#test-the-data-product)


## Installation

Choose the most appropriate installation method for your needs:

### uv

The preferred way to install is [uv](https://docs.astral.sh/uv/):

```
uv tool install --python python3.11 --upgrade 'datacontract-cli[all]'
```

### uvx

If you have [uv](https://docs.astral.sh/uv/) installed, you can run datacontract-cli directly without installing:

```
uv run --with 'datacontract-cli[all]' datacontract --version
```

### pip
Python 3.10, 3.11, and 3.12 are supported. We recommend using Python 3.11.

```bash
python3 -m pip install 'datacontract-cli[all]'
datacontract --version
```

### pip with venv

Typically it is better to install the application in a virtual environment for your projects:

```bash
cd my-project
python3.11 -m venv venv
source venv/bin/activate
pip install 'datacontract-cli[all]'
datacontract --version
```

### pipx

pipx installs into an isolated environment.

```bash
pipx install 'datacontract-cli[all]'
datacontract --version
```

### Docker

You can also use our Docker image to run the CLI tool. It is also convenient for CI/CD pipelines.

```bash
docker pull datacontract/cli
docker run --rm -v ${PWD}:/home/datacontract datacontract/cli
```

You can create an alias for the Docker command to make it easier to use:

```bash
alias datacontract='docker run --rm -v "${PWD}:/home/datacontract" datacontract/cli:latest'
```

_Note:_ The output of Docker command line messages is limited to 80 columns and may include line breaks. Don't pipe docker output to files if you want to export code. Use the `--output` option instead.



## Optional Dependencies (Extras)

The CLI tool defines several optional dependencies (also known as extras) that can be installed for using with specific servers types.
With _all_, all server dependencies are included.

```bash
uv tool install --python python3.11 --upgrade 'datacontract-cli[all]'
```

A list of available extras:

| Dependency                               | Installation Command                       |
|------------------------------------------|--------------------------------------------|
| Amazon Athena                            | `pip install datacontract-cli[athena]`     |
| Avro Support                             | `pip install datacontract-cli[avro]`       |
| Azure Integration                        | `pip install datacontract-cli[azure]`      |
| Google BigQuery                          | `pip install datacontract-cli[bigquery]`   |
| CSV                                      | `pip install datacontract-cli[csv]`        |
| Databricks Integration                   | `pip install datacontract-cli[databricks]` |
| DBML                                     | `pip install datacontract-cli[dbml]`       |
| DuckDB (local/S3/GCS/Azure file testing) | `pip install datacontract-cli[duckdb]`     |
| Excel                                    | `pip install datacontract-cli[excel]`      |
| GCS Integration                          | `pip install datacontract-cli[gcs]`        |
| Iceberg                                  | `pip install datacontract-cli[iceberg]`    |
| Impala                                   | `pip install datacontract-cli[impala]`     |
| Kafka Integration                        | `pip install datacontract-cli[kafka]`      |
| MySQL Integration                        | `pip install datacontract-cli[mysql]`      |
| Oracle                                   | `pip install datacontract-cli[oracle]`     |
| Parquet                                  | `pip install datacontract-cli[parquet]`    |
| PostgreSQL Integration                   | `pip install datacontract-cli[postgres]`   |
| protobuf                                 | `pip install datacontract-cli[protobuf]`   |
| RDF                                      | `pip install datacontract-cli[rdf]`        |
| Amazon Redshift                          | `pip install datacontract-cli[redshift]`   |
| S3 Integration                           | `pip install datacontract-cli[s3]`         |
| Snowflake Integration                    | `pip install datacontract-cli[snowflake]`  |
| Microsoft SQL Server                     | `pip install datacontract-cli[sqlserver]`  |
| Trino                                    | `pip install datacontract-cli[trino]`      |
| API (run as web server)                  | `pip install datacontract-cli[api]`        |


## Documentation

📖 **The full documentation is at [docs.datacontract.com](https://docs.datacontract.com).**

It covers everything in depth, including the complete command reference:

- [Quickstart](https://docs.datacontract.com/quickstart) — install and run your first test
- [Open Data Contract Standard](https://docs.datacontract.com/open-data-contract-standard) — the contract format
- [Test your contract](https://docs.datacontract.com/testing) and [Connect your Data](https://docs.datacontract.com/connect) — schema & quality tests against 18+ data sources
- [Define your Quality Rules](https://docs.datacontract.com/quality-rules) — SQL, library, text, and custom checks
- [Sync with dbt](https://docs.datacontract.com/dbt) · [Edit your contract](https://docs.datacontract.com/editor)
- [Imports](https://docs.datacontract.com/imports) and [Exports](https://docs.datacontract.com/exports) — convert to/from 25+ formats
- [API](https://docs.datacontract.com/api) and [Python Library](https://docs.datacontract.com/python-library)
- [Command reference](https://docs.datacontract.com/commands) — `init`, `lint`, `test`, `export`, `import`, `dbt`, `ci`, `catalog`, `publish`, `api`, and more

## Development Setup

- Install [uv](https://docs.astral.sh/uv/)
- Python base interpreter should be 3.11.x.
- A JDK (17 or 21) must be installed for the Spark-based tests (e.g. `test_test_kafka.py`, `test_test_delta.py`, `test_test_dataframe.py`, `test_import_spark.py`). Java 25 is not yet supported. On macOS and Linux you can install one with [SDKMAN](https://sdkman.io): `sdk install java 21.0.11-tem` (or any 21.x build from `sdk list java`). Verify with `java --version`.
- Docker engine must be running to execute the tests.

```bash
sdk use java 21.0.11-tem
uv python pin 3.11
uv venv
uv pip install -e '.[dev]'
uv run ruff check
uv run pytest
```

## Contribution

We are happy to receive your contributions. Propose your change in an issue or directly create a
pull request with your improvements.

Before creating a pull request, please make sure that all tests are passing (`uv run pytest`) and
your code is properly formatted (`ruff format`). Create a changelog entry and reference fixed
issues (if any).

### Troubleshooting

#### Windows: Some tests fail

Run in WSL. (We need to fix the paths in the tests so that normal Windows will work, contributions are appreciated)

#### PyCharm does not pick up the `.venv` 

This [uv issue](https://github.com/astral-sh/uv/issues/12545) might be relevant.

Try to sync all groups:

```
uv sync --all-groups --all-extras
```

#### Errors in tests that use PySpark (e.g. test_test_kafka.py)

Ensure you have a JDK 17 or 21 installed. Java 25 causes issues.

```
java --version
```


### Docker Build

```bash
docker build -t datacontract/cli .
docker run --rm -v ${PWD}:/home/datacontract datacontract/cli
```

#### Docker compose integration

We've included a [docker-compose.yml](./docker-compose.yml) configuration to simplify the build, test, and deployment of the image.

##### Building the Image with Docker Compose

To build the Docker image using Docker Compose, run the following command:

```bash
docker compose build
```

This command utilizes the `docker-compose.yml` to build the image, leveraging predefined settings such as the build context and Dockerfile location. This approach streamlines the image creation process, avoiding the need for manual build specifications each time.

#### Testing the Image

After building the image, you can test it directly with Docker Compose:

```bash
docker compose run --rm datacontract --version
```

This command runs the container momentarily to check the version of the `datacontract` CLI. The `--rm` flag ensures that the container is automatically removed after the command executes, keeping your environment clean.


## Related Tools

- [Entropy Data](https://www.entropy-data.com/) is a commercial tool to manage data contracts. It contains a web UI, access management, and data governance for a data product marketplace based on data contracts.
- [Data Contract Editor](https://editor.datacontract.com) is an editor for Data Contracts, including a live html preview.

## License

[MIT License](LICENSE)

## Credits

Created by [Stefan Negele](https://www.linkedin.com/in/stefan-negele-573153112/), [Jochen Christ](https://www.linkedin.com/in/jochenchrist/), and [Simon Harrer]().

---

<p align="center">
  <a href="https://entropy-data.com" target="_blank"><img src="https://entropy-data.com/media/entropy-data-logo.svg" alt="Entropy Data" height="36"></a>
</p>
<p align="center">
  <a href="https://entropy-data.com/legal-notice">Legal Notice</a> · <a href="https://entropy-data.com/privacy-policy">Privacy Policy</a>
</p>



<a href="https://github.com/datacontract/datacontract-cli" class="github-corner" aria-label="View source on GitHub"><svg width="80" height="80" viewBox="0 0 250 250" style="fill:#151513; color:#fff; position: absolute; top: 0; border: 0; right: 0;" aria-hidden="true"><path d="M0,0 L115,115 L130,115 L142,142 L250,250 L250,0 Z"></path><path d="M128.3,109.0 C113.8,99.7 119.0,89.6 119.0,89.6 C122.0,82.7 120.5,78.6 120.5,78.6 C119.2,72.0 123.4,76.3 123.4,76.3 C127.3,80.9 125.5,87.3 125.5,87.3 C122.9,97.6 130.6,101.9 134.4,103.2" fill="currentColor" style="transform-origin: 130px 106px;" class="octo-arm"></path><path d="M115.0,115.0 C114.9,115.1 118.7,116.5 119.8,115.4 L133.7,101.6 C136.9,99.2 139.9,98.4 142.2,98.6 C133.8,88.0 127.5,74.4 143.8,58.0 C148.5,53.4 154.0,51.2 159.7,51.0 C160.3,49.4 163.2,43.6 171.4,40.1 C171.4,40.1 176.1,42.5 178.8,56.2 C183.1,58.6 187.2,61.8 190.9,65.4 C194.5,69.0 197.7,73.2 200.1,77.6 C213.8,80.2 216.3,84.9 216.3,84.9 C212.7,93.1 206.9,96.0 205.4,96.6 C205.1,102.4 203.0,107.8 198.3,112.5 C181.9,128.9 168.3,122.5 157.7,114.1 C157.9,116.9 156.7,120.9 152.7,124.9 L141.0,136.5 C139.8,137.7 141.6,141.9 141.8,141.8 Z" fill="currentColor" class="octo-body"></path></svg></a><style>.github-corner:hover .octo-arm{animation:octocat-wave 560ms ease-in-out}@keyframes octocat-wave{0%,100%{transform:rotate(0)}20%,60%{transform:rotate(-25deg)}40%,80%{transform:rotate(10deg)}}@media (max-width:500px){.github-corner:hover .octo-arm{animation:none}.github-corner .octo-arm{animation:octocat-wave 560ms ease-in-out}}</style>
