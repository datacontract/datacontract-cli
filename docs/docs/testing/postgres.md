---
sidebar_position: 17
title: "Postgres"
description: "Create a data contract from your Postgres tables and test the actual data against it — in about 5 minutes."
---

# <img className="page-icon" src="/img/icons/postgres.svg" alt="" /> Postgres

Go from an existing Postgres table to a tested data contract in about five minutes: import the schema straight from Postgres, then test the actual data against it. Works with Postgres and Postgres-compatible databases (e.g. RisingWave).

## 1. Install

```bash
uv tool install --python python3.11 --upgrade 'datacontract-cli[postgres]'
```

See [Installation](../installation.md) for pip, pipx, and Docker.

## 2. Authenticate

Create a `.env` file in your working directory (or export the variables):

```bash
# .env
DATACONTRACT_POSTGRES_USERNAME=postgres
DATACONTRACT_POSTGRES_PASSWORD=mysecretpassword
```

The database user needs `USAGE` on the schema and `SELECT` on the tables. `import` and `test` use the same two variables.

## 3. Create a contract from your tables

Import the table metadata directly from the Postgres catalog. This also generates a ready-to-test `servers` block:

```bash
datacontract import postgres \
  --source localhost \
  --database postgres \
  --schema public \
  --table orders \
  --output datacontract.yaml
```

`--source` is the host of your Postgres server. Add `--port` if it doesn't listen on the default `5432`, repeat `--table` for multiple tables, or omit it to import every table in the schema. `--schema` defaults to `public`.

Only have a DDL file? `datacontract import sql --source orders.sql --dialect postgres` works too, but writes a `servers` block with placeholder values that you have to fill in by hand.

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

Run `datacontract test datacontract.yaml` again: every violation is listed as an error, and the command exits with code `1` — ready for [CI/CD and scheduled runs](../scheduling/index.md) so you catch drift before your consumers do.

## Reference

All authentication options and the data type mappings: **[Postgres Reference](../reference/postgres.md)**.

## Troubleshooting

- **`password authentication failed`** — check the two environment variables above; note that values from an already-set shell variable take precedence over `.env`.
- **`relation does not exist`** — the user lacks `USAGE` on the schema or `SELECT` on the table; a missing grant reads as a missing relation.
