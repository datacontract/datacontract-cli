---
sidebar_position: 20
title: "Spark DataFrame"
description: "Test in-memory Spark DataFrames in a pipeline (programmatic)."
---

# <img className="page-icon" src="/img/icons/spark.svg" alt="" /> Spark DataFrame

Test Spark DataFrames in a pipeline before writing them to a data source. DataFrames are registered as named temporary views; multiple views are supported if the contract has multiple schemas. This connection is used programmatically from Python — no credentials are needed, the existing Spark session is reused.

## 1. Install

Install the `dataframe` extra into the environment your pipeline runs in — this connection is used from Python, so it is a library install rather than a CLI tool:

```bash
pip install 'datacontract-cli[dataframe]'
```

The extra adds the Spark backend of the query engine, not PySpark itself. You already have PySpark wherever you can build the session this connection needs, and on a Spark runtime such as Databricks or EMR a second copy would shadow the one the cluster ships. Outside such a runtime, install PySpark yourself. See [Installation](../installation.md) for pip, pipx, and Docker.

## 2. Create a contract from your DataFrames

Inside an active Spark session, import the schema of registered tables or views:

```bash
datacontract import spark --tables my_table --output datacontract.yaml
```

The generated contract includes a `servers` entry of type `dataframe`:

```yaml
servers:
  - server: production
    type: dataframe
```

## 3. Test the DataFrame

Register the DataFrame as a temporary view named like the schema, then run the test with the Spark session:

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

## 4. Let it catch a violation

The contract becomes valuable when it detects drift. Tighten an expectation — for example, mark a field as `required: true` or add a quality rule — and run the test again: `run.result` becomes `"failed"` and `run.checks` lists each violation, so the assert stops your pipeline before bad data is written.

## Reference

The Spark data type mappings: **[Spark DataFrame Reference](../reference/dataframe.md)**.
