---
sidebar_position: 25
title: "Import: Postgres"
description: "Create a data contract from a Postgres schema."
---

# <img className="page-icon" src="/img/icons/postgres.svg" alt="" /> Import: Postgres

Creates a data contract from a Postgres schema by reading table metadata from `information_schema` — including column types with length and precision, nullability, primary keys, and the comments stored in `pg_description`. Works with Postgres and Postgres-compatible databases (e.g. RisingWave).

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

When permitted, the importer reads PostgreSQL catalog metadata to enrich the contract with declared primary keys and foreign-key relationships. If catalog access is unavailable because the role lacks permission, the table and column import still succeeds: primary keys fall back to `information_schema` when available, and otherwise no key metadata is included.

The supported read-only case is a role with full-table `SELECT`, schema `USAGE`, and ordinary read access to the PostgreSQL catalogs. Column-only grants can produce an incomplete contract, particularly when primary keys use the `information_schema` fallback. Import only the tables that belong together: a foreign-key relationship is included only when both endpoint tables and their properties are present in the selected schema. A declared `NOT VALID` foreign key is imported as a relationship, but its historical validation state is not preserved or reported.

Working from a DDL file instead of a live database? Use [`datacontract import sql --dialect postgres`](./sql.md).

All options: **[`datacontract import postgres`](../commands/import/postgres.md)**.
