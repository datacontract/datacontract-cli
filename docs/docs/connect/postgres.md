---
sidebar_position: 15
title: "Postgres"
description: "Test data in Postgres and Postgres-compatible databases."
---

# Postgres

Test data in Postgres or Postgres-compatible databases (e.g. RisingWave).

## Server

```yaml
servers:
  - server: postgres
    type: postgres
    host: localhost
    port: 5432
    database: postgres
    schema: public
```

## Environment variables

| Variable | Example | Description |
|---|---|---|
| `DATACONTRACT_POSTGRES_USERNAME` | `postgres` | Username |
| `DATACONTRACT_POSTGRES_PASSWORD` | `mysecretpassword` | Password |

Requires the `postgres` extra.
