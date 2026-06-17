---
sidebar_position: 3
title: "Export: dbt Models"
description: "Export a data contract to dbt model schema YAML."
---

# Export: dbt Models

Converts the data contract to dbt models in YAML format, with support for SQL dialects.

```bash
datacontract export dbt-models datacontract.yaml --server snowflake
```

If a server is selected via `--server` (based on its `type`), the dbt column `data_types` match the expected data types of that server. If no server is selected, it defaults to `snowflake`.

See the [dbt Integration](../dbt.md) guide for the full picture, including `datacontract dbt sync`.
