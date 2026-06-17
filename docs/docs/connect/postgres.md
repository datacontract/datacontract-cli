---
sidebar_position: 15
title: "Postgres"
description: "Test data in Postgres and Postgres-compatible databases."
---

# Postgres

Test data in Postgres or Postgres-compatible databases (e.g. RisingWave).

## Example

```yaml
servers:
  postgres:
    type: postgres
    host: localhost
    port: 5432
    database: postgres
    schema: public
models:
  my_table_1:
    type: table
    fields:
      my_column_1:
        type: varchar
```

## Environment variables

| Variable | Example | Description |
|---|---|---|
| `DATACONTRACT_POSTGRES_USERNAME` | `postgres` | Username |
| `DATACONTRACT_POSTGRES_PASSWORD` | `mysecretpassword` | Password |

Requires the `postgres` extra.
