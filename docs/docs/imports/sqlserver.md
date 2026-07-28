---
sidebar_position: 24
title: "Import: SQL Server"
description: "Create a data contract from a SQL Server database."
---

# <img className="page-icon" src="/img/icons/sqlserver.svg" alt="" /> Import: SQL Server

Creates a data contract from a SQL Server database by reading `information_schema` — including column types with length and precision, nullability, and primary keys.

```bash
datacontract import sqlserver \
  --source localhost \
  --database mydb \
  --schema dbo \
  --output datacontract.yaml
```

`--source` is the host of your SQL Server instance. Add `--port` if it doesn't listen on the default `1433`, repeat `--table` to import only specific tables, and set `--schema` if your tables don't live in `dbo`.

The connection uses the same helper as `datacontract test`, so every authentication mode works for the import too: SQL logins, Windows integrated auth, the Entra ID modes, and `az login`.

Types are reconstructed exactly as the test path reads them back, so `varchar(36)`, `decimal(10,2)`, `datetime2` and `varchar(max)` all match on the first run.

The generated contract includes a ready-to-test `servers` block, so you can run `datacontract test datacontract.yaml` immediately afterwards — see the **[SQL Server connection guide](../testing/sqlserver.md)** for the full 5-minute walkthrough and troubleshooting.

Credentials are the same ones `datacontract test` uses: `DATACONTRACT_SQLSERVER_USERNAME` and `DATACONTRACT_SQLSERVER_PASSWORD` — see the [SQL Server Reference](../reference/sqlserver.md).

Only have a DDL script? Use [`datacontract import sql --dialect sqlserver`](./sql.md).
