---
sidebar_position: 16
title: "MySQL"
description: "Create a data contract from your MySQL tables and test the actual data against it."
---

# <img className="page-icon" src="/img/icons/mysql.svg" alt="" /> MySQL

Test data in MySQL or MySQL-compatible databases (e.g. MariaDB).

## 1. Install

```bash
uv tool install --python python3.11 --upgrade 'datacontract-cli[mysql]'
```

See [Installation](../installation.md) for pip, pipx, and Docker.

## 2. Authenticate

Create a `.env` file in your working directory (or export the variables):

```bash
# .env
DATACONTRACT_MYSQL_USERNAME=root
DATACONTRACT_MYSQL_PASSWORD=mysecretpassword
```

## 3. Create a contract from your tables

Import the table metadata directly from the database. This also generates a ready-to-test `servers` block:

```bash
datacontract import mysql \
  --source localhost \
  --database mydb \
  --table orders \
  --output datacontract.yaml
```

`--source` is the host of your MySQL server. Add `--port` if it doesn't listen on the default `3306`, repeat `--table` for multiple tables, or omit it to import every table in the database.

Only have a DDL file? `datacontract import sql --source orders.sql --dialect mysql` works too, but writes a `servers` block with placeholder values that you have to fill in by hand.

## 4. Test the actual data

```bash
datacontract test datacontract.yaml
```

```
Testing datacontract.yaml
Server: mysql (type=mysql, host=localhost, port=3306, database=mydb)
╭────────┬─────────────────────────────────────────────────┬─────────────────┬─────────╮
│ Result │ Check                                           │ Field           │ Details │
├────────┼─────────────────────────────────────────────────┼─────────────────┼─────────┤
│ passed │ Check that field 'order_id' is present          │ orders.order_id │         │
│ passed │ Check that field order_id has no missing values │ orders.order_id │         │
│  ...   │                                                 │                 │         │
╰────────┴─────────────────────────────────────────────────┴─────────────────┴─────────╯
🟢 data contract is valid. Run 24 checks. Took 2.1 seconds.
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

All authentication options and the data type mappings: **[MySQL Reference](../reference/mysql.md)**.

## Troubleshooting

- **`Access denied for user`** — check the two environment variables above and the user's host restrictions (`'user'@'%'` vs `'user'@'localhost'`).
- **`Can't connect to MySQL server`** — host/port in the `servers` block are wrong, or the server doesn't accept remote connections (`bind-address`).
