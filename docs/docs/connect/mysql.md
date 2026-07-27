---
sidebar_position: 15
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

## 2. Set credentials

Create a `.env` file in your working directory (or export the variables):

```bash
# .env
DATACONTRACT_MYSQL_USERNAME=root
DATACONTRACT_MYSQL_PASSWORD=mysecretpassword
```

## 3. Create a contract from your tables

Dump the DDL of a table and import it:

```bash
mysqldump --no-data mydb orders > orders.sql
datacontract import sql --source orders.sql --dialect mysql --output datacontract.yaml
```

The SQL import can't know your connection details, so it writes a `servers` block with placeholder values. Open `datacontract.yaml` and fill in your server:

```yaml
servers:
  - server: mysql
    type: mysql
    host: localhost
    port: 3306
    database: mydb
```

## 4. Test the actual data

```bash
datacontract test datacontract.yaml
```

```
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

Run `datacontract test datacontract.yaml` again: every violation is listed as an error, and the command exits with code `1` — ready for [CI/CD scheduling](../ci-cd.md) so you catch drift before your consumers do.

## Reference

All authentication options and the data type mappings: **[MySQL Reference](../reference/mysql.md)**.

## Troubleshooting

- **`Access denied for user`** — check the two environment variables above and the user's host restrictions (`'user'@'%'` vs `'user'@'localhost'`).
- **`Can't connect to MySQL server`** — host/port in the `servers` block are wrong, or the server doesn't accept remote connections (`bind-address`).
