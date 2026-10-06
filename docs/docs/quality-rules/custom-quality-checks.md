---
sidebar_position: 5
title: "Custom Quality Checks"
description: "Define a parameterised SQL check once, in a folder of YAML files, and use it by name from any data contract."
---

# Custom Quality Checks

A custom quality check is a SQL check defined **once**, outside any contract, and used **by name** from as many contracts as need it. The contract names the check and supplies its arguments; the check holds the query.

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

The folder holds one YAML file per check. The file name is the check's name: `between.yaml` defines `between`.

```yaml
# custom-quality-checks/between.yaml
description: All ${column} values are between ${arguments.min} and ${arguments.max}.
owner: data-platform
dimension: conformity
arguments:
  min:
  max:
queries:
  ansi: |
    SELECT COUNT(*) FROM ${table}
    WHERE ${column} < ${arguments.min} OR ${column} > ${arguments.max}
mustBe: 0
```

| Key | Meaning |
|---|---|
| `description` | What the check verifies. Becomes the check's name in the results, with the placeholders and arguments filled in, unless the rule has a `description` of its own. |
| `owner` | Who maintains the check. Documentation only. |
| `dimension` | The [quality dimension](./index.md#quality-dimensions) the check measures. A `dimension` on the rule takes precedence. |
| `arguments` | The arguments the check takes, each with an optional `type` (`value`, the default, or `identifier`) and `default`. An argument without a `default` is required. |
| `queries` | At least one query, keyed by SQL dialect. |
| `mustBe`, `mustBeGreaterThan`, … | The default expected result, one of the [SQL rule comparators](./sql.md#comparators). |

## Arguments

A **value** argument stands for data the query compares against and becomes a SQL literal: `0`, `'EUR'`, a list becomes `'A', 'B'`. An **identifier** argument names a column or table and becomes a name, quoted like the [placeholders](./sql.md#placeholders):

```yaml
# custom-quality-checks/recent_rows.yaml
arguments:
  timestamp_column: {type: identifier}
  days: {default: 1}
queries:
  ansi: |
    SELECT COUNT(*) FROM ${table}
    WHERE ${arguments.timestamp_column} >= CURRENT_DATE - ${arguments.days} * INTERVAL '1' DAY
mustBeGreaterThan: 0
```

Arguments are always inserted as escaped literals or identifiers, never as raw SQL, so a contract can't alter a check's query. Argument values may use [variables](../configuration.md#variables-in-the-data-contract): `max: ${MAX_AMOUNT}` compares with the number `1000`. A check file can't reference variables itself; pass them in through an argument.

## Placeholders

The queries use the same placeholders as [SQL rules](./sql.md#placeholders) — `${table}`, `${column}`, `${schema}`, and so on. A check whose queries use `${column}` (or `${field}`, `${property}`) can only be declared on a property.

## Dialects

A run uses the query for the [SQL dialect of the server](./sql.md#sql-dialect), and otherwise the `ansi` query:

```yaml
queries:
  ansi: |
    SELECT COUNT(*) FROM ${table}
    WHERE ${arguments.timestamp_column} >= CURRENT_DATE - ${arguments.days} * INTERVAL '1' DAY
  tsql: |
    SELECT COUNT(*) FROM ${table}
    WHERE ${arguments.timestamp_column} >= DATEADD(day, -${arguments.days}, CAST(GETDATE() AS date))
```

The keys are the dialect names in the [SQL dialect table](./sql.md#sql-dialect), so a check for a `mysql` server needs a `duckdb` query. The `ansi` query is optional, but when present it must parse as generic, portable SQL. On SAP HANA, only the `ansi` query runs.

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

## Results

A custom quality check is reported in the `quality` category with the type `field_quality_custom` or `model_quality_custom`. Its `implementation` is the SQL that ran.

| Situation | Result |
|---|---|
| No folder configured, no check by that name, or an invalid check file | `error` |
| An argument that is missing, undeclared or of the wrong kind, a column check on a schema, no expected result | `warning` |
| No query for the server's dialect and no `ansi` query | `warning` |
| A query that is not a single read-only statement | `failed` |

The API server reads the folder from `DATACONTRACT_CUSTOM_QUALITY_CHECKS` in its own environment only; a request cannot choose it.
