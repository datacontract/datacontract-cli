---
sidebar_position: 7
title: "Import: Unity Catalog"
description: "Create a data contract from Databricks Unity Catalog (file or HTTP endpoint)."
---

<img className="page-icon" src="/img/icons/databricks.svg" alt="" />

# Import: Unity Catalog

Creates a data contract from Databricks Unity Catalog, from an exported JSON file or via the HTTP endpoint.

```bash
# From a Unity Catalog JSON file
datacontract import unity --source unity_table.json

# From the HTTP endpoint using a PAT
datacontract import unity --table catalog.schema.table

# From the HTTP endpoint using a Databricks profile
datacontract import unity --table catalog.schema.table
```
