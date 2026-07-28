---
sidebar_position: 5
title: "Import: Databricks"
description: "Create a data contract from Databricks Unity Catalog."
---

# <img className="page-icon" src="/img/icons/databricks.svg" alt="" /> Import: Databricks

Creates a data contract from Databricks Unity Catalog, from an exported JSON file or via the HTTP endpoint.

```bash
# From the HTTP endpoint (repeat --table for multiple tables)
datacontract import databricks --table my_catalog.my_schema.orders

# From an exported Unity Catalog TableInfo JSON file
datacontract import databricks --source unity_table.json
```

For the HTTP endpoint, authenticate either with a personal access token (`DATACONTRACT_DATABRICKS_SERVER_HOSTNAME` + `DATACONTRACT_DATABRICKS_TOKEN`) or with a profile from `~/.databrickscfg` (`DATACONTRACT_DATABRICKS_PROFILE`).

The generated contract includes a ready-to-test `servers` block (`type: databricks` with catalog and schema). To run `datacontract test` afterwards, additionally set `DATACONTRACT_DATABRICKS_HTTP_PATH` to a running SQL warehouse — see the **[Databricks connection guide](../testing/databricks.md)** for the full 5-minute walkthrough and troubleshooting.

The importer was previously called `unity`. That name still works, so existing scripts keep running.
