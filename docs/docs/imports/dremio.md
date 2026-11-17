---
sidebar_position: 13
title: "Import: Dremio"
description: "Create a data contract from the tables and views in a Dremio source, space or folder."
---

# <img className="page-icon" src="/img/icons/database.svg" alt="" /> Import: Dremio

Creates a data contract from the tables and views in a Dremio source, space or folder, however deeply nested, with the full type of every column, including the element types of lists and the fields of structs.

```bash
datacontract import dremio \
  --source localhost \
  --schema lake.sales.marts \
  --output datacontract.yaml
```

`--source` is the host of your Dremio web console, and `--schema` the path of the source, space or folder that holds the datasets: its names separated by periods, a name with a period of its own in double quotes (`$scratch."bucket.v1".raw`). Add `--port` if the REST API doesn't listen on the default `9047`, and repeat `--table` to import only specific tables or views (by default every dataset in the path is imported).

The column types are the ones Dremio reports for a query's results, the same ones `datacontract test` reads back, so `VARCHAR`, `DECIMAL(10,2)`, `ARRAY<VARCHAR>` and `STRUCT<city VARCHAR>` match on the first run. Dremio keeps no `NOT NULL` constraint and no primary key, so no property is `required` or a primary key, and no descriptions are imported.

The generated contract includes a ready-to-test `servers` block, so you can run `datacontract test datacontract.yaml` immediately afterwards. See the **[Dremio connection guide](../testing/dremio.md)** for the full 5-minute walkthrough and troubleshooting.

Credentials are the same ones `datacontract test` uses: see the [Dremio Reference](../reference/dremio.md).

All options: **[`datacontract import dremio`](../commands/import/dremio.md)**.
