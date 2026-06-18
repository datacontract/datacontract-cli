---
sidebar_position: 11
title: "Local files"
description: "Test local files in Parquet, JSON, CSV, or Delta format."
---

<img className="page-icon" src="/img/icons/local.svg" alt="" />

# Local files

:::info Required extra
This connection requires the `duckdb` extra. See [Installation](../installation.md).
:::

Test local files in Parquet, JSON, CSV, or Delta format.

## Server

```yaml
servers:
  - server: local
    type: local
    path: ./*.parquet
    format: parquet
```

