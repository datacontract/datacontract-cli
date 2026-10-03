---
sidebar_position: 4
title: "Apache Hive Reference"
sidebar_label: "Apache Hive"
description: "All Hive authentication options and data type handling."
---

# <img className="page-icon" src="/img/icons/database.svg" alt="" /> Apache Hive Reference

Authentication options and data type handling for [Hive connections](../testing/hive.md).

## Server

```yaml
servers:
  - server: production
    type: hive
    host: hive.acme.com
    port: 10000
    database: sales
```

## Authentication

| Variable | Example | Description |
|---|---|---|
| `DATACONTRACT_HIVE_USERNAME` | `analyst` | Username. Defaults to `hive` |
| `DATACONTRACT_HIVE_PASSWORD` | `mysecretpassword` | Password. Defaults to `hive` |
| `DATACONTRACT_HIVE_AUTH_MECHANISM` | `LDAP` | `PLAIN` (default), `NOSASL`, `LDAP`, or `GSSAPI` (Kerberos) |
| `DATACONTRACT_HIVE_USE_SSL` | `true` | Whether to use TLS. Defaults to `false` |
| `DATACONTRACT_HIVE_USE_HTTP_TRANSPORT` | `true` | Use HTTP transport (`hive.server2.transport.mode=http`) instead of binary thrift. Defaults to `false` |
| `DATACONTRACT_HIVE_HTTP_PATH` | `cliservice` | HTTP path of HiveServer2 for HTTP transport. Defaults to empty |

The defaults fit a HiveServer2 with `hive.server2.authentication=NONE`, which still expects a SASL `PLAIN` handshake with any user name. The connection goes through the [impyla](https://github.com/cloudera/impyla) driver.

`host`, `port`, and `database` come from the contract's `servers` block, and can be overridden with `DATACONTRACT_HIVE_HOST`, `DATACONTRACT_HIVE_PORT`, and `DATACONTRACT_HIVE_DATABASE`. `port` defaults to `10000`.

## Data types

### Importing

`datacontract import hive` reads `DESCRIBE FORMATTED` and takes the declared type as the `physicalType`: `STRING`/`VARCHAR`/`CHAR` → `string`, `INT`/`BIGINT`/`SMALLINT`/`TINYINT` → `integer`, `FLOAT`/`DOUBLE`/`DECIMAL` → `number`, `BOOLEAN` → `boolean`, `DATE` → `date`, `TIMESTAMP` → `timestamp`, `ARRAY<...>` → `array`, `STRUCT<...>` → `object`, `MAP<...>` → `map`, `BINARY` → `string`. Partition columns are imported with the other columns.

### Testing

Hive supports **native type introspection**: the declared `physicalType` is checked against `DESCRIBE`. Length/precision is only enforced when the contract declares it (`varchar` matches `varchar(10)`), and the fields of a `struct` and the element type of an `array` are compared too.
