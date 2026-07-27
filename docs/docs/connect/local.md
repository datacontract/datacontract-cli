---
sidebar_position: 6
title: "Local files"
description: "Test local files in Parquet, JSON, CSV, or Delta format — the fastest way to try the CLI, no credentials needed."
---

# <img className="page-icon" src="/img/icons/local.svg" alt="" /> Local files

Test local files in Parquet, JSON, CSV, or Delta format. This is the fastest way to see the CLI in action — no warehouse, no credentials.

## 1. Install

```bash
uv tool install --python python3.11 --upgrade 'datacontract-cli[duckdb]'
```

See [Installation](../installation.md) for pip, pipx, and Docker.

## 2. Create a contract from a file

Take any CSV file — or use this one, saved as `orders.csv`:

```text
order_id,order_timestamp,customer_id,order_total,status
ORD-1001,2024-01-01T10:00:00Z,CUST-1,4999,delivered
ORD-1002,2024-01-02T11:30:00Z,CUST-2,2500,shipped
ORD-1003,2024-01-03T09:15:00Z,CUST-3,1299,pending
```

Import it. The CLI profiles the data and generates a contract with a schema, value ranges, and a ready-to-test `servers` block:

```bash
datacontract import csv --source orders.csv --output datacontract.yaml
```

## 3. Test the data against the contract

```bash
datacontract test datacontract.yaml
```

```
Testing datacontract.yaml
Server: production (type=local, format=csv, path=orders.csv)
╭────────┬──────────────────────────────────────────────────────┬──────────────┬─────────╮
│ Result │ Check                                                │ Field        │ Details │
├────────┼──────────────────────────────────────────────────────┼──────────────┼─────────┤
│ passed │ Check that field 'order_id' is present               │ order_id     │         │
│ passed │ Check that field order_id has no missing values      │ order_id     │         │
│ passed │ Check that field order_total has a minimum of 1299.0 │ order_total  │         │
│  ...   │                                                      │              │         │
╰────────┴──────────────────────────────────────────────────────┴──────────────┴─────────╯
🟢 data contract is valid. Run 17 checks. Took 1.2 seconds.
```

## 4. Let it catch a violation

Now break the data — append a row with a negative total and a duplicate customer:

```bash
echo 'ORD-1004,2024-01-04T12:00:00Z,CUST-1,-100,delivered' >> orders.csv
datacontract test datacontract.yaml
```

```
🔴 data contract is invalid, found the following errors:
1) customer_id Check that unique field customer_id has no duplicate values:
Actual duplicate_count(customer_id) was 1, expected = 0
2) order_total Check that field order_total has a minimum of 1299.0: Actual
invalid_count(order_total) was 1, expected = 0
```

The command exits with code `1`, so the same call works as a gate in [CI/CD pipelines](../testing.md#scheduling-and-cicd).

Ready for your real data? Do the same against [Snowflake](./snowflake.md), [BigQuery](./bigquery.md), or [Databricks](./databricks.md).

## Server reference

```yaml
servers:
  - server: local
    type: local
    path: ./*.parquet # glob patterns and a {model} placeholder are supported
    format: parquet   # parquet, json, csv, or delta
```

No environment variables are needed for local files. Data type inference and per-format type handling: **[Local Files Reference](../reference/local.md)**.
