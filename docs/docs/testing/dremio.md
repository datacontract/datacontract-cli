---
sidebar_position: 11
title: "Dremio"
description: "Test the tables and views in Dremio sources, spaces and folders against a data contract."
---

# <img className="page-icon" src="/img/icons/database.svg" alt="" /> Dremio

Test tables and views in Dremio, in any source, space or folder, however deeply nested.

## 1. Install

```bash
uv tool install --python python3.11 --upgrade 'datacontract-cli[dremio]'
```

See [Installation](../installation.md) for pip, pipx, and Docker.

## 2. Authenticate

Create a `.env` file in your working directory (or export the variables) with a Dremio user:

```bash
# .env
DATACONTRACT_DREMIO_USERNAME=analyst
DATACONTRACT_DREMIO_PASSWORD=mysecretpassword
```

Or with a personal access token instead:

```bash
# .env
DATACONTRACT_DREMIO_TOKEN=your-personal-access-token
```

The user needs to be able to query the datasets the contract describes. TLS and the other options are in the [Dremio Reference](../reference/dremio.md).

## 3. Create a contract from your tables

Import the tables and views of a source, space or folder, with the full type of every column. This also generates a ready-to-test `servers` block:

```bash
datacontract import dremio \
  --source dremio.acme.com \
  --schema lake.sales.marts \
  --table orders \
  --output datacontract.yaml
```

Repeat `--table` for multiple datasets, or omit it to import every table and view in the path. Add `--port` if the REST API doesn't listen on the default `9047`.

The contract it writes points the `servers` block at the web console of your Dremio, and the `schema` at the path of the source, space or folder that holds the tables. Dremio keeps no `NOT NULL` or unique constraint, so `required` and `unique` below are added by hand:

```yaml
apiVersion: v3.1.0
kind: DataContract
id: orders
name: Orders
version: 1.0.0
status: active
servers:
  - server: production
    type: dremio
    host: dremio.acme.com
    port: 9047
    schema: lake.sales.marts
schema:
  - name: orders
    physicalName: orders
    physicalType: table
    properties:
      - name: order_id
        logicalType: string
        physicalType: VARCHAR
        required: true
        unique: true
      - name: order_total
        logicalType: number
        physicalType: DECIMAL(10,2)
```

The `schema` is a path: its names are separated by periods, and a name that has a period of its own goes in double quotes, the way Dremio SQL writes it (`$scratch."bucket.v1".raw`). Tables are then named by their name alone.

## 4. Test the actual data

```bash
datacontract test datacontract.yaml
```

```
Testing datacontract.yaml
Server: production (type=dremio, host=dremio.acme.com, port=9047, schema=lake.sales.marts)
╭────────┬──────────────────────────────────────────────────────────────┬─────────────┬─────────╮
│ Result │ Check                                                        │ Field       │ Details │
├────────┼──────────────────────────────────────────────────────────────┼─────────────┼─────────┤
│ passed │ Check that field 'order_id' is present                       │ order_id    │         │
│ passed │ Check that field order_id has physical type VARCHAR          │ order_id    │         │
│ passed │ Check that field order_id has no missing values              │ order_id    │         │
│ passed │ Check that unique field order_id has no duplicate values     │ order_id    │         │
│ passed │ Check that field 'order_total' is present                    │ order_total │         │
│ passed │ Check that field order_total has physical type DECIMAL(10,2) │ order_total │         │
╰────────┴──────────────────────────────────────────────────────────────┴─────────────┴─────────╯
🟢 Data contract is valid. Ran 6 checks. Took 1.8 seconds.
```

Each check is a Dremio job, so a test run takes as long as your engine needs to answer a few dozen aggregations.

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

All authentication options and the data type handling: **[Dremio Reference](../reference/dremio.md)**.

## Troubleshooting

- **`Dremio login failed (HTTP 401)`**: the user name and password, or the token, are not accepted.
- **`Object 'orders' not found`**: the `schema` in the `servers` block must be the path of the folder that holds the table. A table in a folder of a file system source (S3, `$scratch`) only appears once Dremio has read its metadata.
- **A connection that times out**: `port` is the port of the web console and REST API (`9047` by default), not the Arrow Flight (`32010`) or JDBC port.
