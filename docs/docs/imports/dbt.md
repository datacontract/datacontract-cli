---
sidebar_position: 12
title: "Import: dbt"
description: "Create a data contract from a dbt manifest file."
---

# <img className="page-icon" src="/img/icons/dbt.svg" alt="" /> Import: dbt

Creates a data contract from a dbt `manifest.json`.

```bash
# Import specific tables
datacontract import dbt --source manifest.json --model orders --model line_items

# Import all tables in the database
datacontract import dbt --source manifest.json
```

A column's `meta` is kept: `classification` becomes the property's `classification`, and the other entries become a custom property named `meta`.

See the [dbt Integration](../dbt.md) guide for the full dbt workflow.

All options: **[`datacontract import dbt`](../commands/import/dbt.md)**.
