---
sidebar_position: 18
title: "Import: Snowflake"
description: "Create a data contract from a Snowflake workspace."
---

<img className="page-icon" src="/img/icons/snowflake.svg" alt="" />

# Import: Snowflake

Creates a data contract from a Snowflake workspace by reading table metadata.

```bash
datacontract import snowflake --source my_database --output datacontract.yaml
```

Snowflake credentials are provided as environment variables (see [Testing](../testing.md)).
