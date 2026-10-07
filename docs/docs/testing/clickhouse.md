---
sidebar_position: 9
title: "ClickHouse"
description: "Create a data contract from your ClickHouse tables and test the actual data against it."
---

# <img className="page-icon" src="/img/icons/clickhouse.svg" alt="" /> ClickHouse

Test data in ClickHouse.

## 1. Install

```bash
uv tool install --python python3.11 --upgrade 'datacontract-cli[clickhouse]'
```

See [Installation](../installation.md) for pip, pipx, and Docker.

## 2. Authenticate

Create a `.env` file in your working directory (or export the variables):

```bash
# .env
DATACONTRACT_CLICKHOUSE_USERNAME=analyst
DATACONTRACT_CLICKHOUSE_PASSWORD=mysecretpassword
```

Without them, the CLI connects as ClickHouse's `default` user with an empty password. For ClickHouse Cloud, set `DATACONTRACT_CLICKHOUSE_SECURE=true` — see the [ClickHouse Reference](../reference/clickhouse.md).

## 3. Create a contract from your tables

Import the table metadata directly from `system.columns`. This also generates a ready-to-test `servers` block:

```bash
datacontract import clickhouse \
  --source localhost \
  --database sales \
  --table orders \
  --output datacontract.yaml
```

Repeat `--table` for multiple tables, or omit it to import every table and view in the database. Add `--port` if the HTTP interface doesn't listen on the default `8123`.

Only have a DDL script? `datacontract import sql --source orders.sql --dialect clickhouse` works too, but writes a `servers` block with placeholder values that you have to fill in by hand.

## 4. Test the actual data

```bash
datacontract test datacontract.yaml
```

```
Testing datacontract.yaml
Server: clickhouse (type=clickhouse, host=localhost, port=8123, database=sales)
╭────────┬────────────────────────────────────────────────────┬──────────┬─────────╮
│ Result │ Check                                              │ Field    │ Details │
├────────┼────────────────────────────────────────────────────┼──────────┼─────────┤
│  ...   │                                                    │          │         │
│ passed │ Check that field 'order_id' is present             │ order_id │         │
│ passed │ Check that field order_id has physical type String │ order_id │         │
│ passed │ Check that field order_id has no missing values    │ order_id │         │
│  ...   │                                                    │          │         │
╰────────┴────────────────────────────────────────────────────┴──────────┴─────────╯
🟢 Data contract is valid. Ran 33 checks. Took 0.5 seconds.
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
        query: SELECT countIf(order_total < 0) FROM orders
        mustBe: 0
```

Run `datacontract test datacontract.yaml` again: every violation is listed as an error, and the command exits with code `1` — ready for [CI/CD and scheduled runs](../scheduling/index.md) so you catch drift before your consumers do.

## Reference

All authentication options and the data type handling: **[ClickHouse Reference](../reference/clickhouse.md)**.

## Troubleshooting

- **`Port 9000 is for clickhouse-client program`** — the CLI talks to ClickHouse over HTTP. A contract that names the native port `9000` (or `9440`) is connected to `8123` (or `8443`) automatically; any other native port has to be replaced by the HTTP port in the `servers` block or with `DATACONTRACT_CLICKHOUSE_PORT`.
- **`Authentication failed`** — set `DATACONTRACT_CLICKHOUSE_USERNAME` and `DATACONTRACT_CLICKHOUSE_PASSWORD`; without them the CLI logs in as `default`.
