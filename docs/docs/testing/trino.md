---
sidebar_position: 21
title: "Trino"
description: "Create a data contract from your Trino tables and test the actual data against it."
---

# <img className="page-icon" src="/img/icons/trino.svg" alt="" /> Trino

Test data in Trino.

## 1. Install

```bash
uv tool install --python python3.11 --upgrade 'datacontract-cli[trino]'
```

See [Installation](../installation.md) for pip, pipx, and Docker.

## 2. Authenticate

Create a `.env` file in your working directory (or export the variables):

```bash
# .env
DATACONTRACT_TRINO_USERNAME=trino
DATACONTRACT_TRINO_PASSWORD=mysecretpassword
```

The default is `basic` auth; JWT and OAuth2 are also supported — see the [Trino Reference](../reference/trino.md).

## 3. Create a contract from your tables

Import the table metadata directly from the catalog. This also generates a ready-to-test `servers` block:

```bash
datacontract import trino \
  --source localhost \
  --catalog my_catalog \
  --schema my_schema \
  --table orders \
  --output datacontract.yaml
```

Repeat `--table` for multiple tables, or omit it to import every table in the schema.

Only have a DDL script? `datacontract import sql --source orders.sql --dialect postgres` works too — Trino's ANSI-style DDL generally parses with that dialect — but writes a `servers` block with placeholder values that you have to fill in by hand.

## 4. Test the actual data

```bash
datacontract test datacontract.yaml
```

```
Testing datacontract.yaml
Server: trino (type=trino, host=localhost, port=8080, catalog=my_catalog, schema=my_schema)
╭────────┬─────────────────────────────────────────────────┬─────────────────┬─────────╮
│ Result │ Check                                           │ Field           │ Details │
├────────┼─────────────────────────────────────────────────┼─────────────────┼─────────┤
│ passed │ Check that field 'order_id' is present          │ orders.order_id │         │
│ passed │ Check that field order_id has no missing values │ orders.order_id │         │
│  ...   │                                                 │                 │         │
╰────────┴─────────────────────────────────────────────────┴─────────────────┴─────────╯
🟢 data contract is valid. Run 24 checks. Took 1.9 seconds.
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

All authentication options (basic, JWT, OAuth2) and the data type handling: **[Trino Reference](../reference/trino.md)**.

## Troubleshooting

- **`401 Unauthorized`** — check the auth mode: password-protected clusters need `basic` credentials over HTTPS; token-based setups need `DATACONTRACT_TRINO_AUTHENTICATION=jwt` and `DATACONTRACT_TRINO_JWT_TOKEN`.
- **`Catalog ... does not exist` / `Schema ... does not exist`** — `catalog` and `schema` in the `servers` block must match `SHOW CATALOGS` / `SHOW SCHEMAS FROM <catalog>`.
