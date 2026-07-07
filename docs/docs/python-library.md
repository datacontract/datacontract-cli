---
sidebar_position: 14
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
| `data_contract_file` | Path or URL to the contract. |
| `data_contract_str` | The contract as a YAML string. |
| `data_contract` | An in-memory `OpenDataContractStandard` object. |
| `server` | Server to test against (the key in `servers`). |
| `schema_name` | Which schema/model to test (default `"all"`). |
| `check_categories` | Set of categories to run: `schema`, `quality`, `servicelevel`, `custom`. |
| `spark` | A `SparkSession`, for the `dataframe` / Databricks engines. |
| `duckdb_connection` | An existing DuckDB connection. |
| `publish_url` | URL to publish test results to. |
| `inline_references` | Resolve external references (default `True`). |
| `include_failed_samples` | Collect a sample of failing rows (default `False`). |

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

See [Spark DataFrame](./connect/dataframe.md) and [Databricks](./connect/databricks.md) for details.

## Credentials

Server credentials are read from environment variables (or a `.env` file), exactly as with the CLI — see [Connect your Data](./connect/index.md). Set them before constructing `DataContract`.
