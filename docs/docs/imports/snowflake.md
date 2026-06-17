---
sidebar_position: 18
title: "Import: Snowflake"
description: "Create a data contract from a Snowflake workspace."
---

# Import: Snowflake

Creates a data contract from a Snowflake workspace by reading table metadata.

```bash
datacontract import snowflake --source my_database --output datacontract.yaml
```

Snowflake credentials are provided as environment variables (see [Data Contract Testing](../testing.md)).
