---
sidebar_position: 25
title: "Import: Postgres"
description: "Create a data contract from a Postgres schema."
---

# <img className="page-icon" src="/img/icons/postgres.svg" alt="" /> Import: Postgres

Creates a data contract from a Postgres schema. Tables and columns are read from `information_schema`, comments from `pg_description`, and key metadata from `pg_catalog`. Works with Postgres and Postgres-compatible databases (e.g. RisingWave).

```bash
datacontract import postgres \
  --source localhost \
  --database postgres \
  --schema public \
  --output datacontract.yaml
```

`--source` is the host of your Postgres server. Add `--port` if it doesn't listen on the default `5432`, and repeat `--table` to import only specific tables (by default every table and view in the schema is imported). `--schema` defaults to `public`.

The generated contract includes a ready-to-test `servers` block, so you can run `datacontract test datacontract.yaml` immediately afterwards — see the **[Postgres connection guide](../testing/postgres.md)** for the full 5-minute walkthrough and troubleshooting.

Credentials are provided as environment variables and are the same ones `datacontract test` uses: `DATACONTRACT_POSTGRES_USERNAME` and `DATACONTRACT_POSTGRES_PASSWORD` — see the [Postgres Reference](../reference/postgres.md).

## Key metadata and privileges

Primary keys and foreign keys are read from the Postgres catalog, so a role with `SELECT` on the tables and `USAGE` on the schema is enough. A foreign key is included only when both of its tables are imported from the same schema.

Working from a DDL file instead of a live database? Use [`datacontract import sql --dialect postgres`](./sql.md).

All options: **[`datacontract import postgres`](../commands/import/postgres.md)**.
