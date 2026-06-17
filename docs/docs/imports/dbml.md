---
sidebar_position: 4
title: "Import: DBML"
description: "Create a data contract from a DBML file, with optional schema/table filters."
---

# Import: DBML

Creates a data contract from a [DBML](https://dbml.dbdiagram.io/) file. You can filter by schema and table name.

```bash
# Import everything
datacontract import dbml --source model.dbml

# Filter by schema(s)
datacontract import dbml --source model.dbml --dbml-schema sales --dbml-schema marketing

# Filter by table name(s)
datacontract import dbml --source model.dbml --dbml-table orders --dbml-table line_items

# Filter by table within a specific schema
datacontract import dbml --source model.dbml --dbml-schema sales --dbml-table orders
```
