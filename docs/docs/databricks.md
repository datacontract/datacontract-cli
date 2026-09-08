---
sidebar_position: 20
title: "Databricks Notebooks and Jobs"
sidebar_label: "Databricks Notebooks"
description: "Run the Data Contract CLI inside a Databricks notebook or job, using the cluster's own Spark session."
---

# <img className="page-icon" src="/img/icons/databricks.svg" alt="" /> Databricks Notebooks and Jobs

Running the CLI **inside** Databricks is different from running it against Databricks from your laptop or CI. The cluster already provides Spark, so the contract is tested through the session you already have — there is no warehouse to point at and nothing to authenticate.

If you are connecting to Databricks *from outside*, you want the [Databricks connection guide](./testing/databricks.md) instead.

## Install the `databricks` extra

```bash
pip install 'datacontract-cli[databricks]'
```

The extra installs no PySpark of its own, so it cannot shadow the build your cluster ships. It contains the Databricks SQL connector and SDK as well, so the SQL-warehouse path keeps working if you use it from the same notebook.

`databricks-runtime` still resolves, as an alias of `databricks`. It used to be the way to get the same set without PySpark; nothing needs the distinction now.

:::tip[Install it as a cluster library, not with `%pip`]
On the Databricks LTS ML runtimes (15.4, 16.4), `%pip install` inside a notebook can fail or leave the environment inconsistent. Add `datacontract-cli[databricks]` as a **PyPI library** on the cluster instead — Compute → your cluster → Libraries → Install new → PyPI — then restart the cluster.
:::

## Test a table in a notebook

Pass the notebook's existing `spark` session. The contract's server needs no credentials — the session is already authenticated as you (or as the job's service principal).

```python
from datacontract.data_contract import DataContract

run = DataContract(
    data_contract_file="/Volumes/acme_catalog_prod/orders_latest/datacontract/datacontract.yaml",
    spark=spark,
).test()

run.result
```

The contract's `servers` block selects the catalog and schema; both are required for a `databricks` server:

```yaml
servers:
  - server: production
    type: databricks
    catalog: acme_catalog_prod
    schema: orders_latest
```

When a Spark session is passed, the CLI uses **that session** — it runs `USE <catalog>.<schema>` on it and reads the tables named by the contract's schema objects. It never opens a SQL-warehouse connection, so `DATACONTRACT_DATABRICKS_HTTP_PATH` and `DATACONTRACT_DATABRICKS_TOKEN` are not needed. Leave `spark` out and the same contract connects through the SQL connector instead, which is what the [Databricks connection guide](./testing/databricks.md) describes.

## Test a DataFrame that is not a table yet

To check data mid-pipeline, before it is written anywhere, register the DataFrame as a temporary view named after the contract's schema object. The same `type: databricks` server works — temporary views live in the session, so they resolve like any other table:

```python
orders_df.createOrReplaceTempView("orders")

run = DataContract(data_contract_file="orders.odcs.yaml", spark=spark).test()
```

Keep `type: databricks` when the contract also describes real Unity Catalog tables. Reach for [`type: dataframe`](./testing/dataframe.md) only when the contract exists purely to validate in-memory DataFrames and has no catalog or schema to name — it is not an ODCS server type, so the CLI writes it as `type: custom` with a `customType` property.

## Fail a job when the contract is violated

`test()` returns the run rather than raising, so a job task decides for itself what a failure means:

```python
run = DataContract(data_contract_file="orders.odcs.yaml", spark=spark).test()

if not run.has_passed():
    raise RuntimeError(f"Data contract violated: {run.result}")
```

Raising marks the task failed, which is what you want for a quality gate between two steps of a Databricks Workflow. To record results instead of stopping the pipeline, inspect `run.checks` and write them somewhere, or [publish them](./entropy-data.md).

For scheduling this outside Databricks, see [Scheduling](./scheduling/index.md).

## Learn more

- **[Databricks](./testing/databricks.md)** — connecting from outside, importing from Unity Catalog, troubleshooting
- **[Databricks Reference](./reference/databricks.md)** — every authentication option and the data type mappings
- **[Python Library](./python-library.md)** — the full `DataContract` API
