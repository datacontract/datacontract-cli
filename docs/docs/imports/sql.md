---
sidebar_position: 1
title: "Import: SQL DDL"
description: "Create a data contract from a SQL DDL file."
---

# Import: SQL

Creates a data contract from a SQL DDL file. Pass the SQL dialect with `--dialect`.

```bash
# Import from a SQL DDL file
datacontract import sql --source my_ddl.sql --dialect postgres

# Save to a file
datacontract import sql --source my_ddl.sql --dialect postgres --output datacontract.yaml
```
