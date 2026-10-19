---
sidebar_position: 15
title: "Import: Hive"
description: "Create a data contract from a Hive database."
---

# <img className="page-icon" src="/img/icons/database.svg" alt="" /> Import: Hive

Creates a data contract from a Hive database by reading `DESCRIBE FORMATTED` for each table — including the full declared column types, the partition columns, and the comments on tables and columns.

```bash
datacontract import hive \
  --source localhost \
  --database sales \
  --output datacontract.yaml
```

`--source` is the host of your HiveServer2. Add `--port` if it doesn't listen on the default `10000`, and repeat `--table` to import only specific tables (by default every table and view in the database is imported).

Hive reports a complete type string, so `varchar(10)`, `decimal(10,2)` and `struct<city:string,zip:string>` are taken verbatim and match what `datacontract test` reads back. Arrays, maps, and structs are expanded into `items`, `map` and nested `properties`.

The generated contract includes a ready-to-test `servers` block, so you can run `datacontract test datacontract.yaml` immediately afterwards — see the **[Hive connection guide](../testing/hive.md)** for the full 5-minute walkthrough and troubleshooting.

Credentials are the same ones `datacontract test` uses — see the [Hive Reference](../reference/hive.md).

Only have a DDL file? Use [`datacontract import sql --dialect hive`](./sql.md).

All options: **[`datacontract import hive`](../commands/import/hive.md)**.
