---
sidebar_position: 8
title: "DuckDB"
description: "Test the tables inside a DuckDB database file."
---

# <img className="page-icon" src="/img/icons/database.svg" alt="" /> DuckDB

Test the tables inside a DuckDB database file.

This is different from [Local files](./local.md): there the CLI reads data *files* (CSV, JSON, Parquet, Delta) through DuckDB, and the contract's `path` points at those files. Here the DuckDB database itself is the data source, and the contract's schema objects are the tables inside it.

## 1. Install

```bash
uv tool install --python python3.11 --upgrade 'datacontract-cli[duckdb]'
```

See [Installation](../installation.md) for pip, pipx, and Docker.

## 2. Describe the server

ODCS carries the path to the database file in the server's `database` field. `schema` is optional and defaults to DuckDB's `main`:

```yaml
servers:
  - server: production
    type: duckdb
    database: ./warehouse.duckdb
    schema: main
schema:
  - name: orders
    properties:
      - name: order_id
        logicalType: string
        physicalType: VARCHAR
        required: true
        unique: true
      - name: order_total
        logicalType: integer
        physicalType: INTEGER
```

Each schema object is looked up as a table of that name in the database. The database file is opened **read-only**, so a test never modifies the data it is testing, and it can run while another process holds the same database open.

## 3. Test the data against the contract

```bash
datacontract test datacontract.yaml
```

## Quality rules

Custom SQL rules are written in DuckDB SQL, and must be [read-only queries](../quality-rules/sql.md):

```yaml
    quality:
      - type: sql
        description: Every order total is one of the allowed amounts.
        query: SELECT count(*) FROM orders WHERE NOT list_contains([100, 200], order_total)
        mustBe: 0
```

## Environment variables

| Environment Variable | Example | Description |
|---|---|---|
| `DATACONTRACT_DUCKDB_DATABASE` | `./warehouse.duckdb` | Path to the DuckDB database file. Overrides the server's `database`. |
| `DATACONTRACT_DUCKDB_SCHEMA` | `sales` | The schema to resolve tables in. Overrides the server's `schema`. |

## Troubleshooting

- **`Table with name ... does not exist`** — the table lives in a schema other than `main`. Set the server's `schema`, so that both the table lookup and the SQL of the quality rules resolve against it.
- **`Could not open the duckdb database`** — the path is resolved relative to the working directory, not to the contract. A database written by a newer DuckDB than the CLI's also fails here.
- **A write in a quality rule fails** — the database is opened read-only, and a quality rule must be a read-only query in any case.
