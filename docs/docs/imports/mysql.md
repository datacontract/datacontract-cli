---
sidebar_position: 17
title: "Import: MySQL"
description: "Create a data contract from a MySQL database."
---

# <img className="page-icon" src="/img/icons/mysql.svg" alt="" /> Import: MySQL

Creates a data contract from a MySQL database by reading `information_schema` — including the full declared column types, nullability, primary keys, and the comments on tables and columns.

```bash
datacontract import mysql \
  --source localhost \
  --database mydb \
  --output datacontract.yaml
```

`--source` is the host of your MySQL server. Add `--port` if it doesn't listen on the default `3306`, and repeat `--table` to import only specific tables (by default every table and view in the database is imported).

The database is reached the way `datacontract test` reaches it: duckdb attaches it through its `mysql` extension, so no extra driver is needed and the import authenticates with the same variables.

The generated contract includes a ready-to-test `servers` block, so you can run `datacontract test datacontract.yaml` immediately afterwards — see the **[MySQL connection guide](../testing/mysql.md)** for the full 5-minute walkthrough and troubleshooting.

Credentials are provided as environment variables and are the same ones `datacontract test` uses: `DATACONTRACT_MYSQL_USERNAME` and `DATACONTRACT_MYSQL_PASSWORD` — see the [MySQL Reference](../reference/mysql.md).

Only have a DDL file? Use [`datacontract import sql --dialect mysql`](./sql.md).
