---
sidebar_position: 4
title: "Apache Impala"
description: "Run checks against an Apache Impala cluster."
---

# Apache Impala

Run checks against an Apache Impala cluster.

## Example

```yaml
servers:
  impala:
    type: impala
    host: my-impala-host
    port: 443
    database: my_database # optional default database
models:
  my_table_1:
    type: table
    # fields as usual …
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

### Type mapping (logicalType → Impala type)

If `physicalType` is not specified, this mapping is recommended:

| logicalType | Recommended Impala type |
|---|---|
| `integer` | `INT` or `BIGINT` |
| `number` | `DOUBLE` / `decimal(..)` |
| `string` | `STRING` or `VARCHAR` |
| `boolean` | `BOOLEAN` |
| `date` | `DATE` |
| `datetime` | `TIMESTAMP` |

Requires the `impala` extra.
