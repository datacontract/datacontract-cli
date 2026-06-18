---
sidebar_position: 1
title: "SQL Quality Rules"
description: "Run a custom SQL query against the data source and compare the result to an expected value or range."
---

# SQL Quality Rules

A `type: sql` rule runs a custom SQL query against the server and compares the single returned value to a threshold. It is the most flexible rule type — use it whenever a check can be expressed as a query. The query runs in the dialect of the selected server.

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

## Comparators

The query must return a single value, which is compared using exactly one of:

| Comparator | Passes when the result… |
|---|---|
| `mustBe` | equals the value |
| `mustNotBe` | does not equal the value |
| `mustBeGreaterThan` / `mustBeGreaterOrEqualTo` | is above a lower bound |
| `mustBeLessThan` / `mustBeLessOrEqualTo` | is below an upper bound |
| `mustBeBetween` / `mustNotBeBetween` | is inside / outside a `[min, max]` range |

## Notes

- **`dialect`** — optionally pin the SQL dialect the query is written in (e.g. `dialect: postgres`). By default the query runs in the selected server's dialect.
- **Referencing the data** — reference the schema/table by its name in the `FROM` clause (e.g. `FROM orders`).
- **`severity`** — set `severity: warning` to report a failing rule without failing the run (see [`--fail-on`](../commands/ci.md)).
