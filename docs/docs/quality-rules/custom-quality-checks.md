---
sidebar_position: 5
title: "Custom Quality Checks"
description: "Define a parameterised SQL check once, in a folder of YAML files, and use it by its ID from any data contract."
---

# Custom Quality Checks

A custom quality check is a SQL check defined **once**, outside any contract, and used **by its ID** from as many contracts as need it. The contract names the check and supplies its arguments; the check holds the query.

```yaml
schema:
  - name: orders
    properties:
      - name: amount
        logicalType: number
        quality:
          - type: custom
            engine: datacontract-cli
            implementation:
              check: between
              arguments:
                min: 0
                max: 10000
```

Point `datacontract test` at the folder the checks live in:

```bash
datacontract test datacontract.yaml --custom-quality-checks ./custom-quality-checks
```

or set `DATACONTRACT_CUSTOM_QUALITY_CHECKS`. See the [`test` command reference](../commands/test.md).

## Defining a check

The folder holds one YAML file per check. The file name is the check's ID (`between.yaml` defines `between`). IDs are unique and must not contain whitespace or any of `/ \ % ; # ?`.

```yaml
# custom-quality-checks/between.yaml
name: Value range
description: All ${column} values are between ${arguments.min} and ${arguments.max}.
owner: data-platform
dimension: conformity
arguments:
  min:
  max:
queries:
  default: |
    SELECT COUNT(*) FROM ${table}
    WHERE ${column} < ${arguments.min} OR ${column} > ${arguments.max}
mustBe: 0
```

| Key | Meaning |
|---|---|
| `name` | A short display name (optional, only used when exporting to Entropy Data). |
| `description` | What the check verifies. Becomes the check's name in the results, with the placeholders and arguments filled in, unless the rule has a `description` of its own. |
| `owner` | Who maintains the check. Documentation only. |
| `dimension` | The [quality dimension](./index.md#quality-dimensions) the check measures. A `dimension` on the rule takes precedence. |
| `arguments` | The arguments the check takes, each with an optional `type` and `default`. See [Arguments](#arguments). |
| `queries` | At least one query, keyed by SQL dialect or `default`. |
| `mustBe`, `mustBeGreaterThan`, … | The default expected result, one of the [SQL rule comparators](./sql.md#comparators). |

## Arguments

A check declares its arguments under `arguments`, and a rule passes their values under `implementation.arguments`. `${arguments.<argumentName>}` in the check definition gets replaced by the respective value:

```yaml
# custom-quality-checks/recent_rows.yaml
arguments:
  timestamp_column: {type: identifier}
  days: {type: number, default: 1}
queries:
  default: |
    SELECT COUNT(*) FROM ${table}
    WHERE ${arguments.timestamp_column} >= CURRENT_DATE - ${arguments.days} * INTERVAL '1' DAY
mustBeGreaterThan: 0
```

```yaml
# datacontract.yaml
implementation:
  check: recent_rows
  arguments:
    timestamp_column: created_at
    days: 7
```

The `type` in the check definition specifies how arguments are parsed:

| Type | Becomes | Example |
|---|---|---|
| `any` (default) | An SQL literal; a list becomes comma-separated literals, as in `IN (...)` | `EUR` → `'EUR'`, `[A, B]` → `'A', 'B'` |
| `number` | A number literal | `"7"` → `7` |
| `identifier` | A column or table name, quoted where needed like the [placeholders](./sql.md#placeholders) | `order date` → `"order date"` |

Values are never inserted as raw SQL. Inside a single-quoted string, an `any` or `number` argument is inserted as escaped text, as in `LIKE '%${arguments.text}%'`.

## Placeholders

The queries use the same placeholders as [SQL rules](./sql.md#placeholders) — `${table}`, `${column}`, `${schema}`, and so on. A check whose queries use `${column}` (or `${field}`, `${property}`) can only be declared on a property. As in placeholders, the `$` in an argument reference is optional: `{arguments.min}` works the same as `${arguments.min}`.

## Dialects

A run uses the query for the [SQL dialect of the server](./sql.md#sql-dialect), and otherwise the `default` query (if it exists):

```yaml
queries:
  default: |
    SELECT COUNT(*) FROM ${table}
    WHERE ${arguments.timestamp_column} >= CURRENT_DATE - ${arguments.days} * INTERVAL '1' DAY
  tsql: |
    SELECT COUNT(*) FROM ${table}
    WHERE ${arguments.timestamp_column} >= DATEADD(day, -${arguments.days}, CAST(GETDATE() AS date))
```

The keys are the dialect names in the [SQL dialect table](./sql.md#sql-dialect), so a check for a `mysql` server needs a `duckdb` query. Write the `default` query in ANSI SQL. Note that on SAP HANA, only the `default` query runs.

## Overriding the expected result

The check's expected result is a default. A comparator on the rule replaces it:

```yaml
quality:
  - type: custom
    engine: datacontract-cli
    implementation:
      check: recent_rows
      arguments:
        timestamp_column: created_at
    mustBeGreaterThan: 10000
```
