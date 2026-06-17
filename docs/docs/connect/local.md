---
sidebar_position: 18
title: "Local files"
description: "Test local files in Parquet, JSON, CSV, or Delta format."
---

# Local files

Test local files in Parquet, JSON, CSV, or Delta format.

## Example

```yaml
servers:
  local:
    type: local
    path: ./*.parquet
    format: parquet
models:
  my_table_1:
    type: table
    fields:
      my_column_1:
        type: varchar
      my_column_2:
        type: string
```

Requires the `duckdb` extra.
