---
sidebar_position: 10
title: "Dremio Reference"
sidebar_label: "Dremio"
description: "All Dremio authentication options and data type handling."
---

# <img className="page-icon" src="/img/icons/database.svg" alt="" /> Dremio Reference

Authentication options and data type handling for [Dremio connections](../testing/dremio.md).

## Server

```yaml
servers:
  - server: production
    type: dremio
    host: dremio.acme.com
    port: 9047
    schema: lake.sales.marts
```

`host` and `port` name the web console of Dremio, whose REST API runs the checks as jobs. `schema` is the path of the source, space or folder the tables are in: names separated by periods, a name with a period of its own in double quotes (`$scratch."bucket.v1".raw`). The checks run in that path, so a table is named by its name alone, however deep the folder is.

## Authentication

| Variable | Example | Description |
|---|---|---|
| `DATACONTRACT_DREMIO_USERNAME` | `analyst` | Username |
| `DATACONTRACT_DREMIO_PASSWORD` | `mysecretpassword` | Password |
| `DATACONTRACT_DREMIO_TOKEN` | `dXNlcm5hbWU...` | Personal access token, used instead of the username and password when set |
| `DATACONTRACT_DREMIO_USE_SSL` | `true` | Whether to connect with HTTPS. Defaults to `false` |
| `DATACONTRACT_DREMIO_VALIDATE_CERTIFICATE` | `false` | Whether to verify the server's TLS certificate. Defaults to `true` |

`host`, `port`, and `schema` come from the contract's `servers` block, and can be overridden with `DATACONTRACT_DREMIO_HOST`, `DATACONTRACT_DREMIO_PORT`, and `DATACONTRACT_DREMIO_SCHEMA`. `port` defaults to `9047`.

The connection goes through Dremio's REST API (`/api/v3/sql` and `/api/v3/job`), so it needs no driver. Dremio Cloud is not supported yet.

## Data types

### Testing

Dremio supports **native type introspection**: the declared `physicalType` is checked against the types Dremio reports for the table's columns (`VARCHAR`, `INTEGER`, `BIGINT`, `DOUBLE`, `FLOAT`, `DECIMAL(10,2)`, `BOOLEAN`, `DATE`, `TIME`, `TIMESTAMP`, `VARBINARY`, `ARRAY<...>`, `STRUCT<...>`, `MAP<...>`).

- Dremio keeps no length for a string, so `VARCHAR(10)`, `CHAR(3)` and `STRING` all match a `VARCHAR` column.
- `LIST<VARCHAR>` and `ARRAY<VARCHAR>` are the same type, and so are `ROW` and `STRUCT`, the spellings `INFORMATION_SCHEMA` reports.
- The precision and scale of a decimal are only enforced when the contract declares them, and the fields of a `STRUCT` and the element type of an `ARRAY` are compared too.

SQL quality rules are written in Dremio SQL.
