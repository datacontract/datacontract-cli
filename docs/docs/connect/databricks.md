---
sidebar_position: 8
title: "Databricks"
description: "Test data in Databricks (Unity Catalog or Hive metastore)."
---

# Databricks

Test data in Databricks. Works with Unity Catalog and the Hive metastore. Needs a running SQL warehouse or compute cluster.

## Example

```yaml
servers:
  production:
    type: databricks
    catalog: acme_catalog_prod
    schema: orders_latest
models:
  orders:
    type: table
    fields: ...
```

## Environment variables

| Variable | Example | Description |
|---|---|---|
| `DATACONTRACT_DATABRICKS_SERVER_HOSTNAME` | `dbc-abcdefgh-1234.cloud.databricks.com` | Host of the SQL warehouse or compute cluster |
| `DATACONTRACT_DATABRICKS_HTTP_PATH` | `/sql/1.0/warehouses/b053a3ff...` | HTTP path to the SQL warehouse or compute cluster |
| `DATACONTRACT_DATABRICKS_TOKEN` | `dapia0000...` | A personal access token (PAT) |
| `DATACONTRACT_DATABRICKS_CLIENT_ID` | `00000000-...` | Service principal client ID for OAuth M2M auth |
| `DATACONTRACT_DATABRICKS_CLIENT_SECRET` | `dose0000...` | Service principal OAuth secret (used with the client ID) |
| `DATACONTRACT_DATABRICKS_PROFILE` | `my-profile` | A profile from `~/.databrickscfg` (Databricks SDK unified auth) |
| `DATACONTRACT_DATABRICKS_AUTH_TYPE` | `databricks-oauth` | Explicit connector auth type, e.g. for interactive U2M browser login |

The authentication method is selected from the variables you set, in this order: PAT → OAuth service principal (`CLIENT_ID` + `CLIENT_SECRET`) → config profile → explicit `AUTH_TYPE`.

## Programmatic (in a notebook or pipeline)

When running in a notebook or pipeline, pass the existing `spark` session — no extra authentication is required (requires Databricks Runtime with Python ≥ 3.10).

```python
from datacontract.data_contract import DataContract

data_contract = DataContract(
  data_contract_file="/Volumes/acme_catalog_prod/orders_latest/datacontract/datacontract.yaml",
  spark=spark)
run = data_contract.test()
run.result
```

:::tip Installing on Databricks compute
On Databricks LTS ML runtimes (15.4, 16.4), installing via `%pip install` in notebooks can cause issues. Instead, add `datacontract-cli[databricks]` as a **PyPI library** on the cluster (Compute → your cluster → Libraries → Install new → PyPI), then restart the cluster.
:::

Requires the `databricks` extra.
