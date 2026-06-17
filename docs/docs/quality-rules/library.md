---
sidebar_position: 2
title: "Library Quality Rules"
description: "Predefined, portable quality checks such as rowCount, nullValues, duplicateValues, invalidValues, and missingValues."
---

# Library Quality Rules

A `type: library` rule is a **predefined, portable check** selected with a `metric` name. Unlike [SQL rules](./sql.md), you don't write a query — the CLI compiles the metric into dialect-specific SQL for the selected server, so the same rule works across all backends.

```yaml
quality:
  - type: library
    metric: nullValues
    mustBe: 0
```

Each rule combines a **metric**, optional **arguments**, and exactly one **comparator** (`mustBe`, `mustBeBetween`, …).

## Supported metrics

| Metric | Level | Measures | Arguments |
|---|---|---|---|
| `rowCount` | schema | Number of rows in the table | — |
| `duplicateValues` | schema or property | Number of duplicate values | schema-level: `properties` (list of columns to check together) |
| `nullValues` | property | Number of `NULL` values | — |
| `missingValues` | property | Number of missing values (`NULL` plus the values you treat as missing) | `missingValues` (list of values counted as missing, e.g. `['', 'N/A']`) |
| `invalidValues` | property | Number of values **not** in an allow-list | `validValues` (list of permitted values) |

:::note
`nullValues`, `missingValues`, and `invalidValues` are only supported at the **property** level. `rowCount` is **schema** level. `duplicateValues` works at either level. Any other metric is reported as "not yet supported".
:::

## Examples

**Row count** (schema level):

```yaml
schema:
  - name: orders
    quality:
      - type: library
        metric: rowCount
        mustBeGreaterThan: 0
```

**No nulls** in a property:

```yaml
quality:
  - type: library
    metric: nullValues
    mustBe: 0
```

**Missing values** — treat empty string and `N/A` as missing, in addition to `NULL`:

```yaml
quality:
  - type: library
    metric: missingValues
    arguments:
      missingValues: [null, '', 'N/A']
    mustBe: 0
```

**Invalid values** — the value must be one of an allow-list:

```yaml
quality:
  - type: library
    metric: invalidValues
    arguments:
      validValues: ['CX-263-DU', 'IK-894-MN', 'ER-399-JY']
    mustBe: 0
```

**Duplicate values** across a set of columns (schema level):

```yaml
schema:
  - name: orders
    quality:
      - type: library
        metric: duplicateValues
        arguments:
          properties: [order_id, line_number]
        mustBe: 0
```

## Comparators

Use exactly one comparator to define the threshold:

| Comparator | Passes when the metric… |
|---|---|
| `mustBe` | equals the value |
| `mustNotBe` | does not equal the value |
| `mustBeGreaterThan` / `mustBeGreaterOrEqualTo` | is above a lower bound |
| `mustBeLessThan` / `mustBeLessOrEqualTo` | is below an upper bound |
| `mustBeBetween` / `mustNotBeBetween` | is inside / outside a `[min, max]` range |

## Percentage thresholds

For the count-of-bad-rows metrics (`nullValues`, `missingValues`, `invalidValues`), set `unit: percent` to compare against a percentage of rows instead of an absolute count:

```yaml
quality:
  - type: library
    metric: nullValues
    unit: percent
    mustBeLessThan: 1   # fewer than 1% of rows are null
```

`unit: percent` is ignored (with a warning) for metrics that are not count-of-bad-rows.
