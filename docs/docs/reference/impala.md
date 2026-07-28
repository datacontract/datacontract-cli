---
sidebar_position: 9
title: "Apache Impala Reference"
sidebar_label: "Apache Impala"
description: "All Impala authentication options and data type handling."
---

# <img className="page-icon" src="/img/icons/impala.svg" alt="" /> Apache Impala Reference

Authentication options and data type handling for [Impala connections](../testing/impala.md).

## Server

```yaml
servers:
  - server: production
    type: impala
    host: my-impala-host
    port: 443
    database: my_database # optional default database
```

## Authentication

| Variable | Example | Description |
|---|---|---|
| `DATACONTRACT_IMPALA_USERNAME` | `analytics_user` | Username |
| `DATACONTRACT_IMPALA_PASSWORD` | `mysecretpassword` | Password |
| `DATACONTRACT_IMPALA_USE_SSL` | `true` | Whether to use SSL (defaults to true) |
| `DATACONTRACT_IMPALA_AUTH_MECHANISM` | `LDAP` | Authentication mechanism (defaults to LDAP) |
| `DATACONTRACT_IMPALA_USE_HTTP_TRANSPORT` | `true` | Whether to use HTTP transport (defaults to true) |
| `DATACONTRACT_IMPALA_HTTP_PATH` | `cliservice` | HTTP path for the Impala service (defaults to cliservice) |

`host`, `port`, and `database` come from the contract's `servers` block.

## Data types

### Importing

There is no direct Impala importer. Import a `SHOW CREATE TABLE` DDL with `datacontract import sql --dialect spark` (Impala DDL is Hive-compatible): `STRING`/`VARCHAR`/`CHAR` → `string`, `INT`/`BIGINT`/`SMALLINT`/`TINYINT` → `integer`, `FLOAT`/`DOUBLE`/`DECIMAL` → `number`, `BOOLEAN` → `boolean`, `DATE` → `date`, `TIMESTAMP` → `timestamp`, `ARRAY<...>` → `array`, `STRUCT<...>` → `object`, `BINARY` → `string` (format `binary`), `MAP<...>` → no logical type.

### Testing

Impala does **not** support native type introspection — the declared `physicalType` is not compared against the catalog. Instead, the `logicalType` is checked by category (`Check that field x has type y`): the actual column type is normalized to one of the nine ODCS categories and compared, with `integer` and `number` treated as compatible.
