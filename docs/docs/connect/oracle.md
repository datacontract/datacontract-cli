---
sidebar_position: 7
title: "Oracle"
description: "Test data in Oracle Database."
---

# Oracle

Test data in Oracle Database.

## Example

```yaml
servers:
  oracle:
    type: oracle
    host: localhost
    port: 1521
    service_name: ORCL
    schema: ADMIN
models:
  my_table_1:
    type: table
    fields:
      my_column_1:
        type: decimal
      my_column_2:
        type: text
        config:
          oracleType: NVARCHAR2 # optional explicit DB type; defaults to a standard mapping
```

## Environment variables

| Variable | Example | Description |
|---|---|---|
| `DATACONTRACT_ORACLE_USERNAME` | `system` | Username |
| `DATACONTRACT_ORACLE_PASSWORD` | `0x162e53` | Password |
| `DATACONTRACT_ORACLE_CLIENT_DIR` | `C:\oracle\client` | Path to an Oracle Instant Client installation (required for thick mode) |

Requires the `oracle` extra.
