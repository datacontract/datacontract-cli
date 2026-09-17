---
sidebar_position: 1
title: "SQL Quality Rules"
description: "Run a custom SQL query against the data source and compare the result to an expected value or range."
---

# SQL Quality Rules

A `type: sql` rule runs a custom SQL query against the server and compares the single returned value to a threshold. It is the most flexible rule type — use it whenever a check can be expressed as a query. The query must be read-only, and is written in the [dialect of the selected server](#sql-dialect).

## Property-level example

```yaml
schema:
  - name: orders
    properties:
      - name: order_total
        logicalType: integer
        physicalType: bigint
        required: true
        quality:
          - type: sql
            description: 95% of all order total values are expected to be between 10 and 499 EUR.
            query: |
              SELECT quantile_cont(order_total, 0.95) AS percentile_95
              FROM orders
            mustBeBetween:
              - 1000
              - 99900
```

## Schema-level example

```yaml
schema:
  - name: orders
    quality:
      - type: sql
        description: The maximum duration between two orders should be less than 3600 seconds.
        query: |
          SELECT MAX(duration) AS max_duration
          FROM (
            SELECT EXTRACT(EPOCH FROM (order_timestamp - LAG(order_timestamp)
                   OVER (ORDER BY order_timestamp))) AS duration
            FROM orders
          ) subquery
        mustBeLessThan: 3600
```

## Placeholders

Instead of hard-coding names, the query can reference the schema, the property, and the location the server names:

| Placeholder | Replaced with |
|---|---|
| `${model}` / `${table}` / `${object}` | the name of the schema object the rule belongs to |
| `${field}` / `${column}` / `${property}` | the name of the property the rule belongs to (property-level rules only) |
| `${schema}` | the server's `schema` |
| `${dataset}` | the server's `dataset` (BigQuery) |
| `${project}` | the server's `project` (BigQuery) |
| `${catalog}` | the server's `catalog` (Databricks, Trino) |
| `${database}` | the server's `database` (Postgres, SQL Server, Snowflake) |

The `$` is optional: `{schema}` works the same as `${schema}`. A placeholder the server has no value for falls back to the name of the schema object.

Any other `${NAME}` or `${NAME:-default}` in the query is an ODCS v3.2.0 [variable reference](../configuration.md#variables-in-the-data-contract), resolved from the environment after the placeholders above. A reference to an unset variable without a default fails the check with the variable's name.

```yaml
quality:
  - type: sql
    description: The orders table is not empty.
    query: |
      SELECT COUNT(*) FROM ${project}.${dataset}.${table}
    mustBeGreaterThan: 0
```

## Comparators

The query must return a single value, which is compared using exactly one of:

| Comparator | Passes when the result… |
|---|---|
| `mustBe` | equals the value |
| `mustNotBe` | does not equal the value |
| `mustBeGreaterThan` / `mustBeGreaterOrEqualTo` | is above a lower bound |
| `mustBeLessThan` / `mustBeLessOrEqualTo` | is below an upper bound |
| `mustBeBetween` / `mustNotBeBetween` | is inside / outside a `[min, max]` range |

## The query must be a query

A rule computes a single value from the data, so the query must be a **single read-only statement** — a `SELECT`, a `WITH … SELECT`, a `UNION`, or a parenthesized query. Anything else is reported as a failed check and never sent to the data source: DDL (`CREATE`, `DROP`, `ALTER`), DML (`INSERT`, `UPDATE`, `DELETE`), `COPY`, `ATTACH`, `INSTALL`/`LOAD`, `SET`, `PRAGMA`, `CALL`, and a second statement appended behind a legitimate one.

This applies to every data source, and to every way the CLI is run. A data contract is not always written by the person whose credentials execute it.

## SQL dialect

There is no `dialect` field on a quality rule. The dialect is **derived from the type of the server the rule runs against**, so a query is read the same way the data source will read it — BigQuery's backtick-quoted table names, Snowflake's `SAMPLE`, SQL Server's `TOP` and Postgres' `->>` are all understood without any declaration:

| Server type | SQL dialect |
|---|---|
| `local`, `s3`, `gcs`, `azure`, `kafka`, `api`, `duckdb` | `duckdb` |
| `postgres` | `postgres` |
| `redshift` | `redshift` |
| `mysql` | `mysql` |
| `oracle` | `oracle` |
| `sqlserver` | `tsql` |
| `snowflake` | `snowflake` |
| `bigquery` | `bigquery` |
| `databricks` | `databricks` |
| `athena` | `athena` |
| `trino` | `trino` |
| `impala` | `hive` |
| `dataframe` | `spark` |

The ODCS synonyms resolve to the spelling above before the dialect is looked up, so `postgresql` is read as `postgres`. A server declared as `type: custom` with `customType: mssql` is read as `tsql`, like `sqlserver`.

Files, Kafka topics and API responses are read through DuckDB, so a rule on those server types is written in DuckDB SQL — including its functions, such as `read_parquet` or `list_contains`.

If a rule fails with *"could not be read as one"*, the query is not valid for the server type the contract declares; the message names the dialect it was read as.

## Notes

- **Referencing the data** — reference the schema/table by its name in the `FROM` clause (e.g. `FROM orders`).
- **`severity`** — set `severity: warning` to report a failing rule without failing the run (see [`--fail-on`](../commands/ci.md)).
