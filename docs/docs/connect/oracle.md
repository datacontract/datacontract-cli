---
sidebar_position: 14
title: "Oracle"
description: "Test data in Oracle Database."
---

<img className="page-icon" src="/img/icons/oracle.svg" alt="" />

# Oracle

:::info Required extra
This connection requires the `oracle` extra. See [Installation](../installation.md).
:::

Test data in Oracle Database.

## Server

```yaml
servers:
  - server: oracle
    type: oracle
    host: localhost
    port: 1521
    service_name: ORCL
    schema: ADMIN
```

## Environment variables

| Variable | Example | Description |
|---|---|---|
| `DATACONTRACT_ORACLE_USERNAME` | `system` | Username |
| `DATACONTRACT_ORACLE_PASSWORD` | `0x162e53` | Password |
| `DATACONTRACT_ORACLE_CLIENT_DIR` | `C:\oracle\client` | Path to an Oracle Instant Client installation (required for thick mode) |

