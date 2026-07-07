---
sidebar_position: 12
title: "Microsoft SQL Server"
description: "Test data in SQL Server, Azure SQL, Synapse, and Fabric."
---

<img className="page-icon" src="/img/icons/sqlserver.svg" alt="" />

# Microsoft SQL Server

:::info[Required extra]
This connection requires the `sqlserver` extra. See [Installation](../installation.md).
:::

Test data in MS SQL Server, including Azure SQL, Synapse Analytics SQL Pool, and Microsoft Fabric.

## Server

```yaml
servers:
  - server: production
    type: sqlserver
    host: localhost
    port: 5432
    database: tempdb
    schema: dbo
    driver: ODBC Driver 18 for SQL Server
```

## Environment variables

| Variable | Example | Description |
|---|---|---|
| `DATACONTRACT_SQLSERVER_AUTHENTICATION` | `sql` | `sql` (default), `cli` (uses `az login`), `windows`, `ActiveDirectoryPassword`, `ActiveDirectoryServicePrincipal`, `ActiveDirectoryInteractive` |
| `DATACONTRACT_SQLSERVER_USERNAME` | `root` | Username (for `sql`, `ActiveDirectoryPassword`, `ActiveDirectoryInteractive`) |
| `DATACONTRACT_SQLSERVER_PASSWORD` | `toor` | Password (for `sql` and `ActiveDirectoryPassword`) |
| `DATACONTRACT_SQLSERVER_CLIENT_ID` | `a3cf5d29-...` | Client ID (for `ActiveDirectoryServicePrincipal`) |
| `DATACONTRACT_SQLSERVER_CLIENT_SECRET` | `kX9~Qr2Lm...` | Client secret (for `ActiveDirectoryServicePrincipal`) |
| `DATACONTRACT_SQLSERVER_TRUST_SERVER_CERTIFICATE` | `True` | Trust self-signed certificate |
| `DATACONTRACT_SQLSERVER_ENCRYPTED_CONNECTION` | `True` | Use SSL |
| `DATACONTRACT_SQLSERVER_DRIVER` | `ODBC Driver 18 for SQL Server` | ODBC driver name |

The `cli` mode reuses an `az login` session through the Azure default credential chain and requires ODBC Driver 18.1 or newer.

