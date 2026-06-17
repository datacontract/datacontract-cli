---
sidebar_position: 4
title: "Apache Impala"
description: "Run checks against an Apache Impala cluster."
---

<img className="page-icon" src="/img/icons/impala.svg" alt="" />

# Apache Impala

:::info Required extra
This connection requires the `impala` extra. See [Installation](../installation.md).
:::

Run checks against an Apache Impala cluster.

## Server

```yaml
servers:
  - server: impala
    type: impala
    host: my-impala-host
    port: 443
    database: my_database # optional default database
```

## Environment variables

| Variable | Example | Description |
|---|---|---|
| `DATACONTRACT_IMPALA_USERNAME` | `analytics_user` | Username |
| `DATACONTRACT_IMPALA_PASSWORD` | `mysecretpassword` | Password |
| `DATACONTRACT_IMPALA_USE_SSL` | `true` | Whether to use SSL (defaults to true) |
| `DATACONTRACT_IMPALA_AUTH_MECHANISM` | `LDAP` | Authentication mechanism (defaults to LDAP) |
| `DATACONTRACT_IMPALA_USE_HTTP_TRANSPORT` | `true` | Whether to use HTTP transport (defaults to true) |
| `DATACONTRACT_IMPALA_HTTP_PATH` | `cliservice` | HTTP path for the Impala service (defaults to cliservice) |

