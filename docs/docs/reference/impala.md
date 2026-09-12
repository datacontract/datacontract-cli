---
sidebar_position: 5
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
    port: 21050 # 443 for a Cloudera Virtual Warehouse
    database: my_database # optional default database
```

## Authentication

| Variable | Example | Description |
|---|---|---|
| `DATACONTRACT_IMPALA_USERNAME` | `analytics_user` | Username |
| `DATACONTRACT_IMPALA_PASSWORD` | `mysecretpassword` | Password |
| `DATACONTRACT_IMPALA_USE_SSL` | `true` | Whether to use SSL. Defaults to `true` |
| `DATACONTRACT_IMPALA_AUTH_MECHANISM` | `LDAP` | `NOSASL` (default), `PLAIN`, `GSSAPI`, or `LDAP` |
| `DATACONTRACT_IMPALA_USE_HTTP_TRANSPORT` | `true` | Whether to use HTTP transport instead of binary thrift. Defaults to `false` |
| `DATACONTRACT_IMPALA_HTTP_PATH` | `cliservice` | HTTP path for the Impala service. Defaults to empty |

Apart from `use_ssl`, these default to the same values as the underlying [impyla](https://github.com/cloudera/impyla) driver.

`host`, `port`, and `database` come from the contract's `servers` block, and can be overridden with `DATACONTRACT_IMPALA_HOST`, `DATACONTRACT_IMPALA_PORT`, and `DATACONTRACT_IMPALA_DATABASE`. `port` defaults to `21050`, Impala's binary thrift port.

### Cloudera Virtual Warehouse

A Cloudera Virtual Warehouse terminates LDAP over HTTPS on port 443, so all three transport options need setting — otherwise the client speaks binary thrift to an HTTPS endpoint and the handshake fails with `TSocket read 0 bytes`:

```bash
# .env
DATACONTRACT_IMPALA_USERNAME=analytics_user
DATACONTRACT_IMPALA_PASSWORD=mysecretpassword
DATACONTRACT_IMPALA_AUTH_MECHANISM=LDAP
DATACONTRACT_IMPALA_USE_HTTP_TRANSPORT=true
DATACONTRACT_IMPALA_HTTP_PATH=cliservice
```

with `port: 443` in the contract's `servers` block.

## Data types

### Importing

There is no direct Impala importer. Import a `SHOW CREATE TABLE` DDL with `datacontract import sql --dialect spark` (Impala DDL is Hive-compatible): `STRING`/`VARCHAR`/`CHAR` → `string`, `INT`/`BIGINT`/`SMALLINT`/`TINYINT` → `integer`, `FLOAT`/`DOUBLE`/`DECIMAL` → `number`, `BOOLEAN` → `boolean`, `DATE` → `date`, `TIMESTAMP` → `timestamp`, `ARRAY<...>` → `array`, `STRUCT<...>` → `object`, `BINARY` → `string` (format `binary`), `MAP<...>` → no logical type.

### Testing

Impala does **not** support native type introspection — the declared `physicalType` is not compared against the catalog. Instead, the `logicalType` is checked by category (`Check that field x has type y`): the actual column type is normalized to one of the nine ODCS categories and compared, with `integer` and `number` treated as compatible.
