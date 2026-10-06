---
sidebar_position: 5
title: "Apache Hive"
description: "Create a data contract from your Hive tables and test the actual data against it."
---

# <img className="page-icon" src="/img/icons/database.svg" alt="" /> Apache Hive

Test data in Apache Hive, through HiveServer2.

## 1. Install

```bash
uv tool install --python python3.11 --upgrade 'datacontract-cli[hive]'
```

See [Installation](../installation.md) for pip, pipx, and Docker.

## 2. Authenticate

A HiveServer2 without authentication (`hive.server2.authentication=NONE`) needs no configuration. For LDAP, create a `.env` file in your working directory (or export the variables):

```bash
# .env
DATACONTRACT_HIVE_USERNAME=analyst
DATACONTRACT_HIVE_PASSWORD=mysecretpassword
DATACONTRACT_HIVE_AUTH_MECHANISM=LDAP
```

Kerberos, TLS, and HTTP transport are configured the same way — see the [Hive Reference](../reference/hive.md).

## 3. Create a contract from your tables

Import the table metadata directly from Hive. This also generates a ready-to-test `servers` block:

```bash
datacontract import hive \
  --source localhost \
  --database sales \
  --table orders \
  --output datacontract.yaml
```

Repeat `--table` for multiple tables, or omit it to import every table and view in the database. Add `--port` if HiveServer2 doesn't listen on the default `10000`.

Only have a DDL script? `datacontract import sql --source orders.sql --dialect hive` works too, but writes a `servers` block with placeholder values that you have to fill in by hand.

## 4. Test the actual data

```bash
datacontract test datacontract.yaml
```

```
Testing datacontract.yaml
Server: hive (type=hive, host=localhost, port=10000, database=sales)
╭────────┬────────────────────────────────────────────────────┬──────────┬─────────╮
│ Result │ Check                                              │ Field    │ Details │
├────────┼────────────────────────────────────────────────────┼──────────┼─────────┤
│  ...   │                                                    │          │         │
│ passed │ Check that field 'order_id' is present             │ order_id │         │
│ passed │ Check that field order_id has physical type string │ order_id │         │
│  ...   │                                                    │          │         │
╰────────┴────────────────────────────────────────────────────┴──────────┴─────────╯
🟢 Data contract is valid. Ran 41 checks. Took 4.4 seconds.
```

Each check is a Hive query, so a test run takes as long as your cluster needs to answer a few dozen aggregations.

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

All authentication options and the data type handling: **[Hive Reference](../reference/hive.md)**.

## Troubleshooting

- **`TSocket read 0 bytes`** — the client and HiveServer2 disagree on the transport: check `DATACONTRACT_HIVE_AUTH_MECHANISM` against `hive.server2.authentication`, and set `DATACONTRACT_HIVE_USE_HTTP_TRANSPORT=true` when `hive.server2.transport.mode=http`.
- **`Table not found`** — the `database` in the `servers` block must contain the table; Hive table names are lower case.
