---
sidebar_position: 4
title: "Export: dbt Sources"
description: "Export a data contract to dbt sources YAML."
---

# Export: dbt Sources

Converts the data contract to a dbt `sources` YAML definition.

```bash
datacontract export dbt-sources datacontract.yaml --server snowflake
```

As with [`dbt-models`](./dbt-models.md), selecting a server maps logical types to that server's data types; otherwise `snowflake` is used.
