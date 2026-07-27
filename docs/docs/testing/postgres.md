---
sidebar_position: 15
title: "Postgres"
description: "Create a data contract from your Postgres tables and test the actual data against it — in about 5 minutes."
---

# <img className="page-icon" src="/img/icons/postgres.svg" alt="" /> Postgres

Go from an existing Postgres table to a tested data contract in about five minutes. Works with Postgres and Postgres-compatible databases (e.g. RisingWave).

## 1. Install

```bash
uv tool install --python python3.11 --upgrade 'datacontract-cli[postgres]'
```

See [Installation](../installation.md) for pip, pipx, and Docker.

## 2. Set credentials

Create a `.env` file in your working directory (or export the variables):

```bash
# .env
DATACONTRACT_POSTGRES_USERNAME=postgres
DATACONTRACT_POSTGRES_PASSWORD=mysecretpassword
```

## 3. Create a contract from your tables

Dump the DDL of a table and import it:

```bash
pg_dump --schema-only --table orders "$DATABASE_URL" > orders.sql
datacontract import sql --source orders.sql --dialect postgres --output datacontract.yaml
```

The SQL import can't know your connection details, so it writes a `servers` block with placeholder values. Open `datacontract.yaml` and fill in your host, port, database, and schema:

```yaml
servers:
  - server: postgres
    type: postgres
    host: localhost
    port: 5432
    database: postgres
    schema: public
```

## 4. Test the actual data

```bash
datacontract test datacontract.yaml
```

```
Testing datacontract.yaml
Server: postgres (type=postgres, host=localhost, port=5432, database=postgres, schema=public)
╭────────┬─────────────────────────────────────────────────┬─────────────────┬─────────╮
│ Result │ Check                                           │ Field           │ Details │
├────────┼─────────────────────────────────────────────────┼─────────────────┼─────────┤
│ passed │ Check that field 'order_id' is present          │ orders.order_id │         │
│ passed │ Check that field order_id has no missing values │ orders.order_id │         │
│  ...   │                                                 │                 │         │
╰────────┴─────────────────────────────────────────────────┴─────────────────┴─────────╯
🟢 data contract is valid. Run 24 checks. Took 2.3 seconds.
```

:::tip[No database at hand?]
The [Quickstart](../quickstart.md) tests a public demo contract against a hosted Postgres database — no setup required.
:::

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

Run `datacontract test datacontract.yaml` again: every violation is listed as an error, and the command exits with code `1` — ready for [CI/CD scheduling](../ci-cd.md) so you catch drift before your consumers do.

## Reference

All authentication options and the data type mappings: **[Postgres Reference](../reference/postgres.md)**.

## Troubleshooting

- **`password authentication failed`** — check the two environment variables above; note that values from an already-set shell variable take precedence over `.env`.
- **`connection refused`** — host/port in the `servers` block are wrong, or the database isn't reachable from your machine (VPN, firewall, `pg_hba.conf`).
- **`relation does not exist`** — the `schema` in the `servers` block doesn't match where the table lives, or the user lacks `USAGE`/`SELECT` grants.
