---
sidebar_position: 20
title: "Import: Unity Catalog"
description: "Create a data contract from Databricks Unity Catalog (file or HTTP endpoint)."
---

# <img className="page-icon" src="/img/icons/databricks.svg" alt="" /> Import: Unity Catalog

Creates a data contract from Databricks Unity Catalog, from an exported JSON file or via the HTTP endpoint.

```bash
# From the HTTP endpoint (repeat --table for multiple tables)
datacontract import unity --table my_catalog.my_schema.orders

# From an exported Unity Catalog TableInfo JSON file
datacontract import unity --source unity_table.json
```

For the HTTP endpoint, authenticate either with a personal access token (`DATACONTRACT_DATABRICKS_SERVER_HOSTNAME` + `DATACONTRACT_DATABRICKS_TOKEN`) or with a profile from `~/.databrickscfg` (`DATACONTRACT_DATABRICKS_PROFILE`).

The generated contract includes a ready-to-test `servers` block (`type: databricks` with catalog and schema). To run `datacontract test` afterwards, additionally set `DATACONTRACT_DATABRICKS_HTTP_PATH` to a running SQL warehouse — see the **[Databricks connection guide](../testing/databricks.md)** for the full 5-minute walkthrough and troubleshooting.
