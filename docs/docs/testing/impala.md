---
sidebar_position: 6
title: "Apache Impala"
description: "Create a data contract from your Impala tables and test the actual data against it."
---

# <img className="page-icon" src="/img/icons/impala.svg" alt="" /> Apache Impala

Run checks against an Apache Impala cluster.

## 1. Install

```bash
uv tool install --python python3.11 --upgrade 'datacontract-cli[impala]'
```

See [Installation](../installation.md) for pip, pipx, and Docker.

## 2. Authenticate

Create a `.env` file in your working directory (or export the variables):

```bash
# .env
DATACONTRACT_IMPALA_USERNAME=analytics_user
DATACONTRACT_IMPALA_PASSWORD=mysecretpassword
```

On a Cloudera Virtual Warehouse, or any cluster reached over HTTPS, also set the transport options listed in the [reference](../reference/impala.md#cloudera-virtual-warehouse).

## 3. Create a contract from your tables

Get the DDL of a table (`SHOW CREATE TABLE orders;` in impala-shell or Hue), save it to a file, and import it. Impala DDL is Hive-compatible, so use the `spark` dialect:

```bash
datacontract import sql --source orders.sql --dialect spark --output datacontract.yaml
```

The SQL import can't know your connection details, so it writes a `servers` block with placeholder values. Open `datacontract.yaml` and fill in your cluster:

```yaml
servers:
  - server: impala
    type: impala
    host: my-impala-host
    port: 21050 # 443 for a Cloudera Virtual Warehouse
    database: my_database # optional default database
```

## 4. Test the actual data

```bash
datacontract test datacontract.yaml
```

```
Testing datacontract.yaml
Server: production (type=impala, host=my-impala-host, port=443, database=my_database)
╭────────┬─────────────────────────────────────────────────┬─────────────────┬─────────╮
│ Result │ Check                                           │ Field           │ Details │
├────────┼─────────────────────────────────────────────────┼─────────────────┼─────────┤
│ passed │ Check that field 'order_id' is present          │ orders.order_id │         │
│ passed │ Check that field order_id has no missing values │ orders.order_id │         │
│  ...   │                                                 │                 │         │
╰────────┴─────────────────────────────────────────────────┴─────────────────┴─────────╯
🟢 data contract is valid. Run 24 checks. Took 2.8 seconds.
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

All authentication options (SSL, transport, auth mechanism) and the data type mappings: **[Impala Reference](../reference/impala.md)**.

## Troubleshooting

- **`TSocket read 0 bytes`** — the client is speaking binary thrift to an HTTPS endpoint. On a Cloudera Virtual Warehouse (or anything else behind an HTTPS load balancer) set `DATACONTRACT_IMPALA_AUTH_MECHANISM=LDAP`, `DATACONTRACT_IMPALA_USE_HTTP_TRANSPORT=true`, and `DATACONTRACT_IMPALA_HTTP_PATH=cliservice`, with `port: 443` in the `servers` block. See the [reference](../reference/impala.md#cloudera-virtual-warehouse).
- **`AuthorizationException`** — the user lacks `SELECT` on the table or the Ranger/Sentry policy doesn't cover the database in the `servers` block.
