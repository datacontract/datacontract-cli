---
sidebar_position: 14
title: "Microsoft SQL Server"
description: "Create a data contract from your SQL Server tables and test the actual data against it."
---

# <img className="page-icon" src="/img/icons/sqlserver.svg" alt="" /> Microsoft SQL Server

Test data in MS SQL Server, including Azure SQL, Synapse Analytics SQL Pool, and Microsoft Fabric.

## 1. Install

```bash
uv tool install --python python3.11 --upgrade 'datacontract-cli[sqlserver]'
```

The connection also requires the [Microsoft ODBC Driver 18 for SQL Server](https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server) on your machine. See [Installation](../installation.md) for pip, pipx, and Docker.

## 2. Authenticate

Create a `.env` file in your working directory (or export the variables):

```bash
# .env
DATACONTRACT_SQLSERVER_USERNAME=sa
DATACONTRACT_SQLSERVER_PASSWORD=mysecretpassword
DATACONTRACT_SQLSERVER_TRUST_SERVER_CERTIFICATE=True # for local/dev servers
```

For Entra ID (Active Directory) authentication modes, see the [SQL Server Reference](../reference/sqlserver.md).

## 3. Create a contract from your tables

Import the table metadata directly from the database. This also generates a ready-to-test `servers` block:

```bash
datacontract import sqlserver \
  --source localhost \
  --database mydb \
  --schema dbo \
  --table orders \
  --output datacontract.yaml
```

`--source` is the host of your SQL Server instance. Add `--port` if it doesn't listen on the default `1433`, repeat `--table` for multiple tables, or omit it to import every table. `--schema` defaults to `dbo`.

Only have a DDL script? `datacontract import sql --source orders.sql --dialect sqlserver` works too, but writes a `servers` block with placeholder values that you have to fill in by hand.

## 4. Test the actual data

```bash
datacontract test datacontract.yaml
```

```
Testing datacontract.yaml
Server: production (type=sqlserver, host=localhost, port=1433, database=mydb, schema=dbo)
╭────────┬─────────────────────────────────────────────────┬─────────────────┬─────────╮
│ Result │ Check                                           │ Field           │ Details │
├────────┼─────────────────────────────────────────────────┼─────────────────┼─────────┤
│ passed │ Check that field 'order_id' is present          │ orders.order_id │         │
│ passed │ Check that field order_id has no missing values │ orders.order_id │         │
│  ...   │                                                 │                 │         │
╰────────┴─────────────────────────────────────────────────┴─────────────────┴─────────╯
🟢 data contract is valid. Run 24 checks. Took 3.7 seconds.
```

## 5. Let it catch a violation

The contract becomes valuable when it detects drift. Tighten an expectation — for example, add a quality rule to a schema in `datacontract.yaml`:

```yaml
schema:
  - name: orders
    # ...
    quality:
      - type: sql
        description: No order has a negative total
        query: SELECT COUNT(*) FROM orders WHERE order_total < 0
        mustBe: 0
```

Run `datacontract test datacontract.yaml` again: every violation is listed as an error, and the command exits with code `1` — ready for [CI/CD and scheduled runs](../scheduling/index.md) so you catch drift before your consumers do.

## Reference

All authentication options (SQL logins, Entra ID modes, `az login`) and the data type mappings: **[SQL Server Reference](../reference/sqlserver.md)**.

## Troubleshooting

- **`Can't open lib 'ODBC Driver 18 for SQL Server'`** — the ODBC driver isn't installed, or its name doesn't match `driver` in the `servers` block / `DATACONTRACT_SQLSERVER_DRIVER`.
- **`SSL Provider: certificate verify failed`** — for servers with self-signed certificates (local Docker, dev), set `DATACONTRACT_SQLSERVER_TRUST_SERVER_CERTIFICATE=True`.
- **`Login failed for user`** — check the authentication mode: SQL logins need `DATACONTRACT_SQLSERVER_AUTHENTICATION=sql` (the default); Entra ID users need one of the `ActiveDirectory*` modes or `cli`.
- **`Could not read model '<table>'`** — the tables must be in the `schema` named in the `servers` block. Without it, the lookup falls back to the login's default schema, usually `dbo`.
