---
sidebar_position: 6
title: "Define your Quality Rules"
description: "Define and run data quality rules in a data contract using ODCS quality checks."
---

# Define your Quality Rules

Beyond schema checks (presence, type, nullability), a data contract can declare **quality rules**. When you run [`datacontract test`](./testing.md), these rules are executed against the data source and reported alongside the schema checks.

Quality rules use the ODCS `quality` attribute, which can be attached either to a **schema** (table/object level) or to an individual **property** (column/field level).

## SQL-based quality rules

The most flexible rule type runs a SQL query against the server and compares the result to an expected range or value. The query runs in the dialect of the selected server.

```yaml
models:
  orders:
    fields:
      order_total:
        type: long
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

Comparators available on a `sql` rule include:

| Comparator | Meaning |
|---|---|
| `mustBe` | Result must equal the value. |
| `mustNotBe` | Result must not equal the value. |
| `mustBeGreaterThan` / `mustBeGreaterThanOrEqualTo` | Lower bound. |
| `mustBeLessThan` / `mustBeLessThanOrEqualTo` | Upper bound. |
| `mustBeBetween` / `mustNotBeBetween` | A `[min, max]` range. |

The query may reference the schema/model by name (e.g. `FROM orders`). Use `{model}` / `{table}` placeholders where supported so the same rule works across servers.

## Field-level constraints

Many common quality expectations can be expressed directly as field constraints in the schema, without writing SQL. These are turned into checks automatically:

```yaml
models:
  orders:
    fields:
      customer_id:
        type: text
        required: true       # no missing values
        unique: true         # no duplicate values
        minLength: 10
        maxLength: 20
      order_status:
        type: text
        enum:                # value must be one of these
          - placed
          - shipped
          - delivered
          - cancelled
```

Constraints such as `required`, `unique`, `minLength`/`maxLength`, `minimum`/`maximum`, `pattern`, and `enum` are validated as part of the `schema`/`quality` checks.

## Running only quality checks

Use `--checks` to restrict a run to quality rules:

```bash
datacontract test --checks quality datacontract.yaml
```

## Where quality rules are used

Quality rules are not only executed by `test` — they are also translated when you export:

- **[dbt](./dbt.md)** — rules become native dbt tests, with `dbt_utils` tests and singular SQL tests for rules that cannot be expressed natively.
- **[SodaCL](./exports/sodacl.md)** — rules become Soda checks.
- **[Great Expectations](./exports/great-expectations.md)** — rules become expectations in a suite.
- **[DQX](./exports/dqx.md)** — rules become Databricks DQX checks.

## Inspecting failing rows

When a quality (or schema) check fails, add `--include-failed-samples` to `test` to collect a small sample of the offending rows (identifier + offending columns; sensitive columns are omitted). This is off by default.

```bash
datacontract test --include-failed-samples datacontract.yaml
```

## Learn more

- The full quality syntax is part of the [Open Data Contract Standard](https://bitol-io.github.io/open-data-contract-standard/latest/).
- For Great Expectations rule authoring, see the [Great Expectations gallery](https://greatexpectations.io/expectations/).
