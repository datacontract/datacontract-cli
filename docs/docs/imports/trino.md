---
sidebar_position: 29
title: "Import: Trino"
description: "Create a data contract from a Trino catalog."
---

# <img className="page-icon" src="/img/icons/trino.svg" alt="" /> Import: Trino

Creates a data contract from a Trino catalog by reading `information_schema`, including the declared column types and nullability.

```bash
datacontract import trino \
  --source localhost \
  --catalog my_catalog \
  --schema my_schema \
  --output datacontract.yaml
```

`--source` is the host of your Trino coordinator. Add `--port` if it doesn't listen on the default `8080`, and repeat `--table` to import only specific tables.

Trino reports a complete type string, so `varchar(36)`, `decimal(10,2)` and `array(varchar)` are taken verbatim and match what `datacontract test` reads back.

The generated contract includes a ready-to-test `servers` block, so you can run `datacontract test datacontract.yaml` immediately afterwards — see the **[Trino connection guide](../testing/trino.md)** for the full 5-minute walkthrough and troubleshooting.

Credentials are the same ones `datacontract test` uses — see the [Trino Reference](../reference/trino.md).

Only have a DDL script? Use [`datacontract import sql --dialect postgres`](./sql.md); Trino's ANSI-style DDL generally parses with that dialect.

All options: **[`datacontract import trino`](../commands/import/trino.md)**.
