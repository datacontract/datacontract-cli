---
sidebar_position: 18
title: "Trino"
description: "Test data in Trino with basic, JWT, or OAuth2 auth."
---

<img className="page-icon" src="/img/icons/trino.svg" alt="" />

# Trino

:::info Required extra
This connection requires the `trino` extra. See [Installation](../installation.md).
:::

Test data in Trino.

## Server

```yaml
servers:
  - server: trino
    type: trino
    host: localhost
    port: 8080
    catalog: my_catalog
    schema: my_schema
```

## Environment variables

| Variable | Example | Description |
|---|---|---|
| `DATACONTRACT_TRINO_USERNAME` | `trino` | Username for `basic` auth |
| `DATACONTRACT_TRINO_PASSWORD` | `mysecretpassword` | Password for `basic` auth |
| `DATACONTRACT_TRINO_AUTHENTICATION` | `oauth2` | `basic` (default), `jwt`, or `oauth2` |
| `DATACONTRACT_TRINO_JWT_TOKEN` | `eyJhbGciOi...` | JWT bearer token for `jwt` auth |

