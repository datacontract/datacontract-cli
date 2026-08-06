---
sidebar_position: 19
title: "Python Library"
description: "Use the Data Contract CLI programmatically as a Python library to test, export, import, lint, and compare data contracts."
---

# Python Library

Everything the CLI does is also available as a Python library through the `DataContract` class. This is useful for embedding data contract checks in pipelines, notebooks, orchestrators (Airflow, Dagster, Prefect), or your own tooling.

```bash
pip install 'datacontract-cli[all]'
```

## Test a data contract

```python
from datacontract.data_contract import DataContract

data_contract = DataContract(data_contract_file="datacontract.yaml")
run = data_contract.test()

if not run.has_passed():
    print("Data quality validation failed.")
    # Abort the pipeline, alert, or take corrective action...
```

### Inspecting the result

`test()` (and `lint()`) return a `Run` object:

```python
run = data_contract.test()

print(run.result)          # "passed", "failed", "warning", or "error"
print(run.has_passed())    # True / False

for check in run.checks:
    print(check.result, check.name, check.reason)
```

## Constructor options

The `DataContract` constructor accepts the contract from a file, a string, or an in-memory ODCS object, plus the same options as the CLI:

```python
from datacontract.data_contract import DataContract

DataContract(
    data_contract_file="datacontract.yaml",  # or data_contract_str=... / data_contract=<ODCS object>
    server="production",                      # which server to test (default: all)
    schema_name="orders",                     # which schema to test (default: "all")
    check_categories={"schema", "quality"},   # subset of: schema, quality, servicelevel, custom
    publish_url="https://api.entropy-data.com/api/test-results",
    inline_references=True,
    include_failed_samples=False,
)
```

| Argument | Description |
|---|---|
| `data_contract_file` | Path, URL, or S3 URL (`s3://bucket/key`) to the contract. |
| `data_contract_str` | The contract as a YAML string. |
| `data_contract` | An in-memory `OpenDataContractStandard` object. |
| `server` | Server to test against (the key in `servers`). |
| `schema_name` | Which schema/model to test (default `"all"`). |
| `check_categories` | Set of categories to run: `schema`, `quality`, `servicelevel`, `custom`. |
| `spark` | A `SparkSession`, for the `dataframe` / Databricks engines. |
| `duckdb_connection` | An existing DuckDB connection. |
| `publish_url` | URL to publish test results to. |
| `ssl_verification` | Verify TLS certificates when publishing (default `True`). |
| `inline_references` | Resolve external references (default `True`). |
| `include_failed_samples` | Collect a sample of failing rows (default `False`). |
| `config` | Credentials and connection options, as a `Config` object or dict (see [Credentials](#credentials)). |

## Lint a data contract

```python
from datacontract.data_contract import DataContract

run = DataContract(data_contract_file="datacontract.yaml").lint()
assert run.has_passed()
```

## Export

`export()` returns the converted artifact as a string (or bytes for binary formats such as Excel). Pass the target format and, optionally, a schema and format-specific keyword arguments.

```python
from datacontract.data_contract import DataContract

data_contract = DataContract(data_contract_file="datacontract.yaml", server="snowflake")

sql = data_contract.export("sql")
print(sql)

# Format-specific options are passed as keyword arguments
html = data_contract.export("html")
with open("datacontract.html", "w") as f:
    f.write(html)
```

See [Exports](./exports/index.md) for the full list of formats.

## Import

`DataContract.import_from_source()` is a class method that returns an ODCS (`OpenDataContractStandard`) object. Format-specific options are passed as keyword arguments.

```python
from datacontract.data_contract import DataContract

odcs = DataContract.import_from_source(
    format="sql",
    source="my_ddl.sql",
    dialect="postgres",
)

# Wrap it to export or test
data_contract = DataContract(data_contract=odcs)
print(data_contract.export("odcs"))
```

See [Imports](./imports/index.md) for the full list of formats.

## Publish a data contract

`publish()` uploads the contract to Entropy Data (or a Data Mesh Manager / Data Contract Manager instance), the same as `datacontract publish`. It returns the URL of the published contract, if the server reports one, and raises a `DataContractException` if publishing fails.

```python
from datacontract.data_contract import DataContract
from datacontract.model.exceptions import DataContractException

data_contract = DataContract(data_contract_file="datacontract.yaml")

try:
    url = data_contract.publish()
    print(f"Published to {url}")
except DataContractException as e:
    print(f"Publishing failed: {e.reason}")
```

The host and the API key are read from `ENTROPY_DATA_HOST` and `ENTROPY_DATA_API_KEY`, or can be passed explicitly:

```python
from datacontract import Config

DataContract(
    data_contract_file="datacontract.yaml",
    config=Config(entropy_data_api_key=get_secret("entropy-data")),
).publish()
```

## Compare two contracts (changelog)

```python
from datacontract.data_contract import DataContract

v1 = DataContract(data_contract_file="v1.odcs.yaml")
v2 = DataContract(data_contract_file="v2.odcs.yaml")

result = v1.changelog(v2)
print(result)
```

## Spark DataFrames and Databricks

Pass a `SparkSession` to test in-memory DataFrames (registered as temporary views) or to run inside a Databricks notebook:

```python
from datacontract.data_contract import DataContract

df.createOrReplaceTempView("my_table")

data_contract = DataContract(
    data_contract_file="datacontract.yaml",
    spark=spark,
)
run = data_contract.test()
assert run.result == "passed"
```

See [Spark DataFrame](./testing/dataframe.md) and [Databricks](./testing/databricks.md) for details.

## Credentials

Server credentials are read from environment variables (or a `.env` file), exactly as with the CLI — see [Configuration](./configuration.md) for all mechanisms and their precedence.

They can also be passed programmatically via the `config` argument, without touching the process environment. The typed `Config` class declares every supported option; field names match the environment variable names (`snowflake_username` ↔ `DATACONTRACT_SNOWFLAKE_USERNAME`), unset fields fall back to the environment, and secrets are held as `SecretStr` so they stay out of logs and reprs:

```python
from datacontract import Config
from datacontract.data_contract import DataContract

run = DataContract(
    data_contract_file="datacontract.yaml",
    server="production",
    config=Config(
        snowflake_username="svc_test",
        snowflake_password=get_secret("snowflake"),
        snowflake_role="TESTER",
    ),
).test()
```

A plain dict keyed by the environment variable names is accepted as well: `config={"DATACONTRACT_SNOWFLAKE_PASSWORD": "..."}`. `DataContract.import_from_source()` takes the same `config` argument. The config object is passed explicitly through the connection layer, so concurrent tests with different credentials in one process do not interfere.

A YAML config file works for both the CLI (`--config-file`, defaulting to `./datacontract-config.yaml` or `~/.datacontract/config.yaml`) and the library (`Config.from_yaml(path)`). Sections map to option names, and `${VAR}` references resolve from the environment at load time, so the file can be committed without holding secrets:

```yaml
# datacontract-config.yaml
snowflake:
  username: svc_test
  password: ${SNOWFLAKE_PASSWORD}
  role: TESTER
max_errors: 10
```
