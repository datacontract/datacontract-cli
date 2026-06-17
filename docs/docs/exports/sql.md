---
sidebar_position: 1
title: "Export: SQL DDL"
description: "Convert a data contract into a SQL data definition language (DDL) file."
---

# Export: SQL

Converts a data contract into a SQL data definition language (DDL) file.

```bash
datacontract export sql datacontract.yaml --output output.sql
```

The SQL dialect is determined from the `servers` block in the data contract (e.g. `type: postgres`, `type: snowflake`). Alternatively, pass it explicitly:

```bash
datacontract export sql datacontract.yaml --dialect postgres --output output.sql
```

Supported dialects: `postgres`, `mysql`, `snowflake`, `databricks`, `sqlserver`, `trino`, `oracle`, `clickhouse` (and `auto`, the default, which detects the dialect from the server type).

:::note Databricks `variant` columns
If an error is thrown when deploying SQL DDLs with `variant` columns on Databricks, set:

```python
spark.conf.set("spark.databricks.delta.schema.typeCheck.enabled", "false")
```
:::

## ClickHouse

```bash
datacontract export sql datacontract.yaml --dialect clickhouse --output ddl.sql
```

ClickHouse requires a table engine (default `ENGINE = MergeTree()`) and uses `ORDER BY` as its primary key mechanism. Primary key fields in the contract are translated to the `ORDER BY` clause.

```bash
# Custom engine
datacontract export sql datacontract.yaml --dialect clickhouse \
  --clickhouse-engine "ReplicatedMergeTree('/clickhouse/tables/{shard}/table', '{replica}')"

# Custom ORDER BY (defaults to primary key columns if defined)
datacontract export sql datacontract.yaml --dialect clickhouse \
  --clickhouse-order-by "event_date DESC, event_id"
```

| Option | Description |
|---|---|
| `--clickhouse-engine` | The table engine. Default: `MergeTree()`. |
| `--clickhouse-order-by` | Comma-separated `ORDER BY` columns. Defaults to primary key columns. |

Override any field's ClickHouse type individually by setting the custom property `clickhouseType` in the data contract.
