---
sidebar_position: 7
title: "Databricks"
description: "Create a data contract from Unity Catalog and test the actual data against it — in about 5 minutes."
---

# <img className="page-icon" src="/img/icons/databricks.svg" alt="" /> Databricks

Go from an existing Unity Catalog table to a tested data contract in about five minutes: import the schema from Unity Catalog, then test the actual data on a SQL warehouse. Works with Unity Catalog and the Hive metastore; testing needs a running SQL warehouse or compute cluster.

## 1. Install

```bash
uv tool install --python python3.11 --upgrade 'datacontract-cli[databricks]'
```

See [Installation](../installation.md) for pip, pipx, and Docker.

## 2. Authenticate

Create a `.env` file in your working directory (or export the variables):

```bash
# .env
DATACONTRACT_DATABRICKS_SERVER_HOSTNAME=dbc-abcdefgh-1234.cloud.databricks.com
DATACONTRACT_DATABRICKS_HTTP_PATH=/sql/1.0/warehouses/b053a3ff69ee87a8
DATACONTRACT_DATABRICKS_TOKEN=<your-personal-access-token>
```

Find the hostname and HTTP path under your SQL warehouse's **Connection details** tab. For OAuth service principals and profile-based auth, see the [Databricks Reference](../reference/databricks.md).

## 3. Create a contract from your tables

Import the table metadata directly from Unity Catalog. This also generates a ready-to-test `servers` block:

```bash
datacontract import databricks \
  --table my_catalog.my_schema.orders \
  --output datacontract.yaml
```

Repeat `--table` for multiple tables.

## 4. Test the actual data

```bash
datacontract test datacontract.yaml
```

```
Testing datacontract.yaml
Server: databricks (type=databricks, catalog=my_catalog, schema=my_schema)
╭────────┬─────────────────────────────────────────────────┬─────────────────┬─────────╮
│ Result │ Check                                           │ Field           │ Details │
├────────┼─────────────────────────────────────────────────┼─────────────────┼─────────┤
│ passed │ Check that field 'order_id' is present          │ orders.order_id │         │
│ passed │ Check that field order_id has no missing values │ orders.order_id │         │
│  ...   │                                                 │                 │         │
╰────────┴─────────────────────────────────────────────────┴─────────────────┴─────────╯
🟢 data contract is valid. Run 24 checks. Took 8.4 seconds.
```

## 5. Let it catch a violation

The contract becomes valuable when it detects drift. Tighten an expectation — for example, add a quality rule to a schema in `datacontract.yaml`:

```yaml
schema:
  - name: orders
    # ...
    quality:
      - type: sql
        description: No order has a negative total
        query: SELECT COUNT(*) FROM orders WHERE order_total < 0
        mustBe: 0
```

Run `datacontract test datacontract.yaml` again: every violation is listed as an error, and the command exits with code `1` — ready for [CI/CD and scheduled runs](../scheduling/index.md) so you catch drift before your consumers do.

## Reference

All authentication options (PAT, OAuth M2M, profiles, precedence order) and the data type mappings: **[Databricks Reference](../reference/databricks.md)**.

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

:::tip[Installing on Databricks compute]
The same `databricks` extra works there — it installs no PySpark of its own, so it cannot shadow the build the cluster ships. On the LTS ML runtimes (15.4, 16.4), installing via `%pip install` in notebooks can cause issues — add `datacontract-cli[databricks]` as a **PyPI library** on the cluster instead (Compute → your cluster → Libraries → Install new → PyPI), then restart the cluster.

See **[Databricks Notebooks and Jobs](../databricks.md)** for the full walkthrough.
:::

## Troubleshooting

- **`Invalid HTTP path`, or the test hangs** — `DATACONTRACT_DATABRICKS_HTTP_PATH` must point at a running SQL warehouse or cluster (check the **Connection details** tab). `import databricks` works without it, but `test` requires it.
- **`403 Invalid access token`** — the PAT is expired or belongs to a different workspace than `DATACONTRACT_DATABRICKS_SERVER_HOSTNAME`.
- **`TABLE_OR_VIEW_NOT_FOUND`** — the token's principal lacks `USE CATALOG`/`USE SCHEMA`/`SELECT` privileges on the table.
