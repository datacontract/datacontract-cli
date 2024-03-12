# Data Contract CLI

<p>
  <a href="https://github.com/datacontract/cli/actions/workflows/ci.yaml?query=branch%3Amain">
    <img alt="Test Workflow" src="https://img.shields.io/github/actions/workflow/status/datacontract/cli/ci.yaml?branch=main"></a>
  <a href="https://github.com/datacontract/cli">
    <img alt="Stars" src="https://img.shields.io/github/stars/datacontract/cli" /></a>
  <a href="https://datacontract.com/slack" rel="nofollow"><img src="https://camo.githubusercontent.com/5ade1fd1e76a6ab860802cdd2941fe2501e2ca2cb534e5d8968dbf864c13d33d/68747470733a2f2f696d672e736869656c64732e696f2f62616467652f736c61636b2d6a6f696e5f636861742d77686974652e7376673f6c6f676f3d736c61636b267374796c653d736f6369616c" alt="Slack Status" data-canonical-src="https://img.shields.io/badge/slack-join_chat-white.svg?logo=slack&amp;style=social" style="max-width: 100%;"></a>
</p>

The `datacontract` CLI is an open source command-line tool for working with [Data Contracts](https://datacontract.com/).
It uses data contract YAML files to lint the data contract, connect to data sources and execute schema and quality tests, detect breaking changes, and export to different formats. The tool is written in Python. It can be used as a standalone CLI tool, in a CI/CD pipeline, or directly as a Python library.

![Main features of the Data Contract CLI](datacontractcli.png)

## Getting started

Let's look at this data contract:
[https://datacontract.com/examples/orders-latest/datacontract.yaml](https://datacontract.com/examples/orders-latest/datacontract.yaml)

We have a _servers_ section with endpoint details to the S3 bucket, _models_ for the structure of the data, and _quality_ attributes that describe the expected freshness and number of rows.

This data contract contains all information to connect to S3 and check that the actual data meets the defined schema and quality requirements. We can use this information to test if the actual data set in S3 is compliant to the data contract.

Let's use [pip](https://pip.pypa.io/en/stable/getting-started/) to install the CLI (or use the [Docker image](#docker), if you prefer).
```bash
$ python3 -m pip install datacontract-cli
```

We run the tests:

```bash
$ datacontract test https://datacontract.com/examples/orders-latest/datacontract.yaml

# returns:
Testing https://datacontract.com/examples/orders-latest/datacontract.yaml
╭────────┬─────────────────────────────────────────────────────────────────────┬───────────────────────────────┬─────────╮
│ Result │ Check                                                               │ Field                         │ Details │
├────────┼─────────────────────────────────────────────────────────────────────┼───────────────────────────────┼─────────┤
│ passed │ Check that JSON has valid schema                                    │ orders                        │         │
│ passed │ Check that JSON has valid schema                                    │ line_items                    │         │
│ passed │ Check that field order_id is present                                │ orders                        │         │
│ passed │ Check that field order_timestamp is present                         │ orders                        │         │
│ passed │ Check that field order_total is present                             │ orders                        │         │
│ passed │ Check that field customer_id is present                             │ orders                        │         │
│ passed │ Check that field customer_email_address is present                  │ orders                        │         │
│ passed │ row_count >= 5000                                                   │ orders                        │         │
│ passed │ Check that required field order_id has no null values               │ orders.order_id               │         │
│ passed │ Check that unique field order_id has no duplicate values            │ orders.order_id               │         │
│ passed │ duplicate_count(order_id) = 0                                       │ orders.order_id               │         │
│ passed │ Check that required field order_timestamp has no null values        │ orders.order_timestamp        │         │
│ passed │ freshness(order_timestamp) < 24h                                    │ orders.order_timestamp        │         │
│ passed │ Check that required field order_total has no null values            │ orders.order_total            │         │
│ passed │ Check that required field customer_email_address has no null values │ orders.customer_email_address │         │
│ passed │ Check that field lines_item_id is present                           │ line_items                    │         │
│ passed │ Check that field order_id is present                                │ line_items                    │         │
│ passed │ Check that field sku is present                                     │ line_items                    │         │
│ passed │ values in (order_id) must exist in orders (order_id)                │ line_items.order_id           │         │
│ passed │ row_count >= 5000                                                   │ line_items                    │         │
│ passed │ Check that required field lines_item_id has no null values          │ line_items.lines_item_id      │         │
│ passed │ Check that unique field lines_item_id has no duplicate values       │ line_items.lines_item_id      │         │
╰────────┴─────────────────────────────────────────────────────────────────────┴───────────────────────────────┴─────────╯
🟢 data contract is valid. Run 22 checks. Took 6.739514 seconds.
```

Voilà, the CLI tested that the _datacontract.yaml_ itself is valid, all records comply with the schema, and all quality attributes are met.

## Usage

```bash
# create a new data contract from example and write it to datacontract.yaml
$ datacontract init datacontract.yaml

# lint the datacontract.yaml
$ datacontract lint datacontract.yaml

# execute schema and quality checks
$ datacontract test datacontract.yaml

# execute schema and quality checks on the examples within the contract
$ datacontract test --examples datacontract.yaml

# find differences between to data contracts (Coming Soon)
$ datacontract diff datacontract-v1.yaml datacontract-v2.yaml

# fail pipeline on breaking changes  (Coming Soon)
$ datacontract breaking datacontract-v1.yaml datacontract-v2.yaml

# export model as jsonschema (other formats: avro, dbt, dbt-sources, dbt-staging-sql, jsonschema, odcs, rdf, sql (coming soon), sodacl, terraform)
$ datacontract export --format jsonschema datacontract.yaml

# import sql
$ datacontract import --format sql --source my_ddl.sql

# import protobuf as model (Coming Soon)
$ datacontract import --format protobuf --source my_protobuf_file.proto datacontract.yaml
```

## Programmatic (Python)
```python
from datacontract.data_contract import DataContract

data_contract = DataContract(data_contract_file="datacontract.yaml")
run = data_contract.test()
if not run.has_passed():
    print("Data quality validation failed.")
    # Abort pipeline, alert, or take corrective actions...
```

## Scenario: Integration with Data Mesh Manager

If you use [Data Mesh Manager](https://datamesh-manager.com/), you can use the data contract URL and append the `--publish` option to send and display the test results. Set an environment variable for your API key.

```bash
# Fetch current data contract, execute tests on production, and publish result to data mesh manager
$ EXPORT DATAMESH_MANAGER_API_KEY=xxx
$ datacontract test https://demo.datamesh-manager.com/demo279750347121/datacontracts/4df9d6ee-e55d-4088-9598-b635b2fdcbbc/datacontract.yaml --server production --publish
```





## Installation

Choose the most appropriate installation method for your needs:

### pip
Python 3.11 recommended.
Python 3.12 available as pre-release release candidate for 0.9.3

```bash
python3 -m pip install datacontract-cli
```

### pipx
pipx installs into an isolated environment.
```bash
pipx install datacontract-cli
```

### Docker

```bash
docker pull datacontract/cli
docker run --rm -v ${PWD}:/home/datacontract datacontract/cli
```

Or via an alias that automatically uses the latest version:

```bash
alias datacontract='docker run --rm -v "${PWD}:/home/datacontract" datacontract/cli:latest'
```

## Documentation

### Tests

Data Contract CLI can connect to data sources and run schema and quality tests to verify that the data contract is valid.

```bash
$ datacontract test --server production datacontract.yaml
```

To connect to the databases the `server` block in the datacontract.yaml is used to set up the connection. In addition, credentials, such as username and passwords, may be defined with environment variables.

The application uses different engines, based on the server `type`.

| Type         | Format     | Description                                                               | Status      | Engines                             |
|--------------|------------|---------------------------------------------------------------------------|-------------|-------------------------------------|
| `s3`         | `parquet`  | Works for any S3-compliant endpoint., e.g., AWS S3, GCS, MinIO, Ceph, ... | ✅           | soda-core-duckdb                    |
| `s3`         | `json`     | Support for `new_line` delimited JSON files and one JSON record per file. | ✅           | fastjsonschema<br> soda-core-duckdb |
| `s3`         | `csv`      |                                                                           | ✅           | soda-core-duckdb                    |
| `s3`         | `delta`    |                                                                           | Coming soon | TBD                                 |
| `postgres`   | n/a        |                                                                           | ✅           | soda-core-postgres                  |
| `snowflake`  | n/a        |                                                                           | ✅           | soda-core-snowflake                 |
| `bigquery`   | n/a        |                                                                           | ✅           | soda-core-bigquery                  |
| `redshift`   | n/a        |                                                                           | Coming soon | TBD                                 |
| `databricks` | n/a        | Support for Databricks SQL with Unity catalog and Hive metastore.         | ✅           | soda-core-spark                     |
| `databricks` | n/a        | Support for Spark for programmatic use in Notebooks.                      | ✅           | soda-core-spark-df                  |
| `kafka`      | `json`     | Experimental.                                                             | ✅           | pyspark<br>soda-core-spark-df       |
| `kafka`      | `avro`     |                                                                           | Coming soon | TBD                                 |
| `kafka`      | `protobuf` |                                                                           | Coming soon | TBD                                 |
| `local`      | `parquet`  |                                                                           | ✅           | soda-core-duckdb                    |
| `local`      | `json`     | Support for `new_line` delimited JSON files and one JSON record per file. | ✅           | fastjsonschema<br> soda-core-duckdb |
| `local`      | `csv`      |                                                                           | ✅           | soda-core-duckdb                    |

Feel free to create an issue, if you need support for an additional type.

### S3

Data Contract CLI can test data that is stored in S3 buckets or any S3-compliant endpoints in various formats.

#### Example

datacontract.yaml
```yaml
servers:
  production:
    type: s3
    endpointUrl: https://minio.example.com # not needed with AWS S3
    location: s3://bucket-name/path/*/*.json
    format: json
    delimiter: new_line # new_line, array, or none
```

#### Environment Variables

| Environment Variable              | Example                       | Description           |
|-----------------------------------|-------------------------------|-----------------------|
| `DATACONTRACT_S3_REGION`            | `eu-central-1`                  | Region of S3 bucket   |
| `DATACONTRACT_S3_ACCESS_KEY_ID`     | `AKIAXV5Q5QABCDEFGH`            | AWS Access Key ID     |
| `DATACONTRACT_S3_SECRET_ACCESS_KEY` | `93S7LRrJcqLaaaa/XXXXXXXXXXXXX` | AWS Secret Access Key |


### Postgres

Data Contract CLI can test data in Postgres or Postgres-compliant databases (e.g., RisingWave).

#### Example

datacontract.yaml
```yaml
servers:
  postgres:
    type: postgres
    host: localhost
    port: 5432
    database: postgres
    schema: public
models:
  my_table_1: # corresponds to a table
    type: table
    fields: 
      my_column_1: # corresponds to a column
        type: varchar
```

#### Environment Variables

| Environment Variable             | Example            | Description |
|----------------------------------|--------------------|-------------|
| `DATACONTRACT_POSTGRES_USERNAME` | `postgres`         | Username    |
| `DATACONTRACT_POSTGRES_PASSWORD` | `mysecretpassword` | Password    |


### Snowflake

Data Contract CLI can test data in Snowflake.

#### Example

datacontract.yaml
```yaml

servers:
  snowflake:
    type: snowflake
    account: abcdefg-xn12345
    database: ORDER_DB
    schema: ORDERS_PII_V2
models:
  my_table_1: # corresponds to a table
    type: table
    fields: 
      my_column_1: # corresponds to a column
        type: varchar
```

#### Environment Variables

| Environment Variable               | Example            | Description                                         |
|------------------------------------|--------------------|-----------------------------------------------------|
| `DATACONTRACT_SNOWFLAKE_USERNAME`  | `datacontract`     | Username                                            |
| `DATACONTRACT_SNOWFLAKE_PASSWORD`  | `mysecretpassword` | Password                                            |
| `DATACONTRACT_SNOWFLAKE_ROLE`      | `DATAVALIDATION`   | The snowflake role to use.                          |
| `DATACONTRACT_SNOWFLAKE_WAREHOUSE` | `COMPUTE_WH`       | The Snowflake Warehouse to use executing the tests. |


### BigQuery

We support authentication to BigQuery using Service Account Key. The used Service Account should include the roles:
* BigQuery Job User
* BigQuery Data Viewer


#### Example

datacontract.yaml
```yaml
servers:
  production:
    type: bigquery
    project: datameshexample-product
    dataset: datacontract_cli_test_dataset
models:
  datacontract_cli_test_table: # corresponds to a BigQuery table
    type: table
    fields: ...
```

#### Environment Variables

| Environment Variable                         | Example                   | Description                                             |
|----------------------------------------------|---------------------------|---------------------------------------------------------|
| `DATACONTRACT_BIGQUERY_ACCOUNT_INFO_JSON_PATH` | `~/service-access-key.json` | Service Access key as saved on key creation by BigQuery |


### Databricks

Works with Unity Catalog and Hive metastore.

Needs a running SQL warehouse or compute cluster.

#### Example

datacontract.yaml
```yaml
servers:
  production:
    type: databricks
    host: dbc-abcdefgh-1234.cloud.databricks.com
    catalog: acme_catalog_prod
    schema: orders_latest
models:
  orders: # corresponds to a table
    type: table
    fields: ...
```

#### Environment Variables

| Environment Variable                         | Example                              | Description                                           |
|----------------------------------------------|--------------------------------------|-------------------------------------------------------|
| `DATACONTRACT_DATABRICKS_TOKEN` | `dapia00000000000000000000000000000` | The personal access token to authenticate             |
| `DATACONTRACT_DATABRICKS_HTTP_PATH` | `/sql/1.0/warehouses/b053a3ffffffff` | The HTTP path to the SQL warehouse or compute cluster |


### Databricks (programmatic)

Works with Unity Catalog and Hive metastore.
When running in a notebook or pipeline, the provided `spark` session can be used.
An additional authentication is not required.

Requires a Databricks Runtime with Python >= 3.10.

#### Example

datacontract.yaml
```yaml
servers:
  production:
    type: databricks
    host: dbc-abcdefgh-1234.cloud.databricks.com # ignored, always use current host
    catalog: acme_catalog_prod
    schema: orders_latest
models:
  orders: # corresponds to a table
    type: table
    fields: ...
```

Notebook
```python
%pip install datacontract-cli
dbutils.library.restartPython()

from datacontract.data_contract import DataContract

data_contract = DataContract(
  data_contract_file="/Volumes/acme_catalog_prod/orders_latest/datacontract/datacontract.yaml", 
  spark=spark)
run = data_contract.test()
run.result
```

### Kafka

Kafka support is currently considered experimental.

#### Example

datacontract.yaml
```yaml
servers:
  production:
    type: kafka
    host: abc-12345.eu-central-1.aws.confluent.cloud:9092
    topic: my-topic-name
    format: json
```

#### Environment Variables

| Environment Variable               | Example | Description                 |
|------------------------------------|---------|-----------------------------|
| `DATACONTRACT_KAFKA_SASL_USERNAME` | `xxx`   | The SASL username (key).    |
| `DATACONTRACT_KAFKA_SASL_PASSWORD` | `xxx`   | The SASL password (secret). |



### Exports

```bash
# Example export to dbt model
datacontract export --format dbt
```

Available export options:

| Type               | Description                                             | Status |
|--------------------|---------------------------------------------------------|--------|
| `jsonschema`       | Export to JSON Schema                                   | ✅      | 
| `odcs`             | Export to Open Data Contract Standard (ODCS)            | ✅      | 
| `sodacl`           | Export to SodaCL quality checks in YAML format          | ✅      |
| `dbt`              | Export to dbt models in YAML format                     | ✅      |
| `dbt-sources`      | Export to dbt sources in YAML format                    | ✅      |
| `dbt-staging-sql`  | Export to dbt staging SQL models                        | ✅      |
| `rdf`              | Export data contract to RDF representation in N3 format | ✅      |
| `avro`             | Export to AVRO models                                   | ✅      |
| `protobuf`         | Export to Protobuf                                      | ✅      |
| `terraform`        | Export to terraform resources                           | ✅      |
| `pydantic`         | Export to pydantic models                               | TBD    |
| `sql`              | Export to SQL DDL                                       | TBD    |
| Missing something? | Please create an issue on GitHub                        | TBD    |

#### RDF

The export function converts a given data contract into a RDF representation. You have the option to 
add a base_url which will be used as the default prefix to resolve relative IRIs inside the document.

```shell
datacontract export --format rdf --rdf-base https://www.example.com/ datacontract.yaml
```

The data contract is mapped onto the following concepts of a yet to be defined Data Contract
Ontology named https://datacontract.com/DataContractSpecification/ :
- DataContract
- Server
- Model

Having the data contract inside an RDF Graph gives us access the following use cases:
- Interoperability with other data contract specification formats
- Store data contracts inside a knowledge graph
- Enhance a semantic search to find and retrieve data contracts
- Linking model elements to already established ontologies and knowledge
- Using full power of OWL to reason about the graph structure of data contracts
- Apply graph algorithms on multiple data contracts (Find similar data contracts, find "gatekeeper"
data products, find the true domain owner of a field attribute)

### Imports

```bash
# Example import from SQL DDL
datacontract import --format sql --source my_ddl.sql
```

Available import options:

| Type               | Description                                    | Status  |
|--------------------|------------------------------------------------|---------|
| `sql`              | Import from SQL DDL                            | ✅       | 
| `protobuf`         | Import from Protobuf schemas                   | TBD     |
| `avro`             | Import from AVRO schemas                       | TBD     |
| `jsonschema`       | Import from JSON Schemas                       | TBD     |
| `dbt`              | Import from dbt models                         | TBD     |
| `odcs`             | Import from Open Data Contract Standard (ODCS) | TBD     |
| Missing something? | Please create an issue on GitHub               | TBD     |

## Development Setup

Python base interpreter should be 3.11.x (unless working on 3.12 release candidate).

```bash
# create venv
python3 -m venv venv
source venv/bin/activate

# Install Requirements
pip install --upgrade pip setuptools wheel
pip install -e '.[dev]'
cd tests/
pytest
```

Release

```bash
git tag v0.9.0
git push origin v0.9.0
python3 -m pip install --upgrade build twine
rm -r dist/
python3 -m build
# for now only test.pypi.org
python3 -m twine upload --repository testpypi dist/*
```

Docker Build

```bash
docker build -t datacontract/cli .
docker run --rm -v ${PWD}:/home/datacontract datacontract/cli
```

## Release Steps

1. Update the version in `pyproject.toml`
2. Have a look at the `CHANGELOG.md`
3. Create release commit manually
4. Execute `./release`
5. Wait until GitHub Release is created
6. Add the release notes to the GitHub Release

## Contribution

We are happy to receive your contributions. Propose your change in an issue or directly create a pull request with your improvements.

## License

[MIT License](LICENSE)

## Credits

Created by [Stefan Negele](https://www.linkedin.com/in/stefan-negele-573153112/) and [Jochen Christ](https://www.linkedin.com/in/jochenchrist/).



<a href="https://github.com/datacontract/cli" class="github-corner" aria-label="View source on GitHub"><svg width="80" height="80" viewBox="0 0 250 250" style="fill:#151513; color:#fff; position: absolute; top: 0; border: 0; right: 0;" aria-hidden="true"><path d="M0,0 L115,115 L130,115 L142,142 L250,250 L250,0 Z"></path><path d="M128.3,109.0 C113.8,99.7 119.0,89.6 119.0,89.6 C122.0,82.7 120.5,78.6 120.5,78.6 C119.2,72.0 123.4,76.3 123.4,76.3 C127.3,80.9 125.5,87.3 125.5,87.3 C122.9,97.6 130.6,101.9 134.4,103.2" fill="currentColor" style="transform-origin: 130px 106px;" class="octo-arm"></path><path d="M115.0,115.0 C114.9,115.1 118.7,116.5 119.8,115.4 L133.7,101.6 C136.9,99.2 139.9,98.4 142.2,98.6 C133.8,88.0 127.5,74.4 143.8,58.0 C148.5,53.4 154.0,51.2 159.7,51.0 C160.3,49.4 163.2,43.6 171.4,40.1 C171.4,40.1 176.1,42.5 178.8,56.2 C183.1,58.6 187.2,61.8 190.9,65.4 C194.5,69.0 197.7,73.2 200.1,77.6 C213.8,80.2 216.3,84.9 216.3,84.9 C212.7,93.1 206.9,96.0 205.4,96.6 C205.1,102.4 203.0,107.8 198.3,112.5 C181.9,128.9 168.3,122.5 157.7,114.1 C157.9,116.9 156.7,120.9 152.7,124.9 L141.0,136.5 C139.8,137.7 141.6,141.9 141.8,141.8 Z" fill="currentColor" class="octo-body"></path></svg></a><style>.github-corner:hover .octo-arm{animation:octocat-wave 560ms ease-in-out}@keyframes octocat-wave{0%,100%{transform:rotate(0)}20%,60%{transform:rotate(-25deg)}40%,80%{transform:rotate(10deg)}}@media (max-width:500px){.github-corner:hover .octo-arm{animation:none}.github-corner .octo-arm{animation:octocat-wave 560ms ease-in-out}}</style>
