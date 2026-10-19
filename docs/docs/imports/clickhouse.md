---
sidebar_position: 8
title: "Import: ClickHouse"
description: "Create a data contract from a ClickHouse database."
---

# <img className="page-icon" src="/img/icons/clickhouse.svg" alt="" /> Import: ClickHouse

Creates a data contract from a ClickHouse database by reading `system.tables` and `system.columns` — including the full declared column types, the sorting key, and the comments on tables and columns.

```bash
datacontract import clickhouse \
  --source localhost \
  --database sales \
  --output datacontract.yaml
```

`--source` is the host of your ClickHouse server. Add `--port` if its HTTP interface doesn't listen on the default `8123`, and repeat `--table` to import only specific tables (by default every table and view in the database is imported).

ClickHouse reports a complete type string, so `Nullable(String)`, `LowCardinality(String)` and `Decimal(10, 2)` are taken verbatim and match what `datacontract test` reads back. A column is `required` unless its type is `Nullable`, and the columns of the sorting key become the primary key.

The generated contract includes a ready-to-test `servers` block, so you can run `datacontract test datacontract.yaml` immediately afterwards — see the **[ClickHouse connection guide](../testing/clickhouse.md)** for the full 5-minute walkthrough and troubleshooting.

Credentials are the same ones `datacontract test` uses — see the [ClickHouse Reference](../reference/clickhouse.md).

Only have a DDL file? Use [`datacontract import sql --dialect clickhouse`](./sql.md).

All options: **[`datacontract import clickhouse`](../commands/import/clickhouse.md)**.
