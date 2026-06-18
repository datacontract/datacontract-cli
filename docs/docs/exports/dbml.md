---
sidebar_position: 17
title: "Export: DBML"
description: "Export a data contract to DBML (Database Markup Language) for diagrams and documentation."
---

<img className="page-icon" src="/img/icons/database.svg" alt="" />

# Export: DBML

Converts the data contract to [DBML](https://dbml.dbdiagram.io/) (Database Markup Language).

```bash
datacontract export dbml datacontract.yaml --output schema.dbml
```

If a server is selected via `--server`, the logical data types are converted to that database's specific types (based on the server `type`). If no server is selected, the logical data types are exported.
