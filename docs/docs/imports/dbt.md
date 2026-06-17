---
sidebar_position: 2
title: "Import: dbt"
description: "Create a data contract from a dbt manifest file."
---

<img className="page-icon" src="/img/icons/generic.svg" alt="" />

# Import: dbt

Creates a data contract from a dbt `manifest.json`.

```bash
# Import specific tables
datacontract import dbt --source manifest.json --dbt-model orders --dbt-model line_items

# Import all tables in the database
datacontract import dbt --source manifest.json
```

See the [dbt Integration](../dbt.md) guide for the full dbt workflow.
