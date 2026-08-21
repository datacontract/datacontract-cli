---
sidebar_position: 16
title: "Oracle"
description: "Create a data contract from your Oracle tables and test the actual data against it."
---

# <img className="page-icon" src="/img/icons/oracle.svg" alt="" /> Oracle

Test data in Oracle Database.

## 1. Install

```bash
uv tool install --python python3.11 --upgrade 'datacontract-cli[oracle]'
```

See [Installation](../installation.md) for pip, pipx, and Docker.

## 2. Authenticate

Create a `.env` file in your working directory (or export the variables):

```bash
# .env
DATACONTRACT_ORACLE_USERNAME=system
DATACONTRACT_ORACLE_PASSWORD=mysecretpassword
```

## 3. Create a contract from your tables

Import the table metadata directly from the database. This also generates a ready-to-test `servers` block:

```bash
datacontract import oracle \
  --source localhost \
  --service-name ORCL \
  --schema ADMIN \
  --table ORDERS \
  --output datacontract.yaml
```

`--source` is the host and `--service-name` the service. Repeat `--table` for multiple tables, or omit it to import every table in the schema; Oracle upper-cases identifiers, so `--schema` is upper-cased for you.

Only have a DDL script? `datacontract import sql --source orders.sql --dialect oracle` works too, but writes a `servers` block with placeholder values that you have to fill in by hand.

## 4. Test the actual data

```bash
datacontract test datacontract.yaml
```

```
Testing datacontract.yaml
Server: oracle (type=oracle, host=localhost, port=1521, schema=ADMIN)
╭────────┬─────────────────────────────────────────────────┬─────────────────┬─────────╮
│ Result │ Check                                           │ Field           │ Details │
├────────┼─────────────────────────────────────────────────┼─────────────────┼─────────┤
│ passed │ Check that field 'order_id' is present          │ orders.order_id │         │
│ passed │ Check that field order_id has no missing values │ orders.order_id │         │
│  ...   │                                                 │                 │         │
╰────────┴─────────────────────────────────────────────────┴─────────────────┴─────────╯
🟢 data contract is valid. Run 24 checks. Took 3.4 seconds.
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

All authentication options and the data type mappings: **[Oracle Reference](../reference/oracle.md)**.

## Troubleshooting

- **`ORA-12514: TNS:listener does not currently know of service`** — `service_name` in the `servers` block doesn't match the database service; check with `lsnrctl status` or your DBA.
- **`DPY-3010: connections to this database server version are not supported`** — older Oracle versions need thick mode: install the Oracle Instant Client and set `DATACONTRACT_ORACLE_CLIENT_DIR`.
- **`ORA-00942: table or view does not exist`** — the `schema` in the `servers` block must be the owning schema (in uppercase), and the user needs `SELECT` on the table.
