---
sidebar_position: 7
title: "Define your Schema"
description: "The ODCS schema and property attributes that datacontract test verifies automatically: presence, types, required, unique, primary keys, and logicalTypeOptions."
---

# Define your Schema

The `schema` block describes the structure of the data: the schemas (tables, views, topics, files) and their properties (columns, fields). Many of its attributes are **automatically verified** by [`datacontract test`](./testing/index.md) — you declare them once and they become executable checks on every run, on every backend.

This page covers only those attributes. Everything else in the `schema` block is documentation, carried into exports but never asserted against the data.

```bash
datacontract test --checks schema datacontract.yaml
```

## What generates a check

| Attribute | Level | Check |
|---|---|---|
| *(any property)* | property | The column exists in the data source |
| `physicalType` | property | The column's native type matches (catalog backends only) |
| `logicalType` | property | The column's type matches, normalized to an ODCS category |
| `required` | property | No missing values |
| `unique` | property | No duplicate values |
| `primaryKey` | property | No missing values **and** no duplicates |
| `logicalTypeOptions.minLength` / `maxLength` | property | Value length within bounds |
| `logicalTypeOptions.minimum` / `maximum` | property | Value within bounds (inclusive) |
| `logicalTypeOptions.exclusiveMinimum` / `exclusiveMaximum` | property | Value within bounds (exclusive) |
| `logicalTypeOptions.pattern` | property | Value matches the regular expression |
| `logicalTypeOptions.enum` | property | Value is one of the listed values |
| `logicalTypeOptions.minItems` / `maxItems` | array property | Number of elements within bounds |
| `logicalTypeOptions.uniqueItems` | array property | Elements of the array are distinct |
| `quality` | schema, property | See [Define your Quality Rules](./quality-rules/index.md) |

A contract that uses all of them:

```yaml
schema:
  - name: orders
    physicalName: orders_v2
    properties:
      - name: order_id
        logicalType: string
        physicalType: varchar(36)
        primaryKey: true
      - name: order_status
        logicalType: string
        required: true
        logicalTypeOptions:
          enum: ['pending', 'shipped', 'delivered']
      - name: order_total
        logicalType: integer
        physicalType: integer
        logicalTypeOptions:
          minimum: 0
          maximum: 1000000
      - name: customer_email
        logicalType: string
        logicalTypeOptions:
          maxLength: 255
          pattern: '^[^@]+@[^@]+$'
      - name: tags
        logicalType: array
        items:
          logicalType: string
        logicalTypeOptions:
          minItems: 1
          maxItems: 10
          uniqueItems: true
```

## Presence and naming

Every property produces a **presence check** — the column must exist in the data source. This is the one check you always get, even for a property that declares nothing but a name.

`physicalName` selects the real object in the data source; `name` is the logical name used in the contract. When `physicalName` is set, the checks run against it:

```yaml
schema:
  - name: orders            # logical name
    physicalName: orders_v2 # the real table
    properties:
      - name: total
        physicalName: order_total   # the real column
```

## Types

A property can declare a portable `logicalType`, a native `physicalType`, or both. Which one is checked depends on the backend:

- **`physicalType`** is compared against the column's real declared type read from the platform catalog. This applies on the nine backends with catalog introspection: Snowflake, BigQuery, Databricks, Postgres, Redshift, SQL Server, Oracle, Trino, and Athena. It takes precedence over `logicalType`.
- **`logicalType`** is used everywhere else, and as the fallback when the native type cannot be read. Both the declared and the actual type are normalized to an ODCS category before comparison, so `integer` and `number` are mutually compatible.

Properties of `logicalType: object` or `array` that declare `properties` or `items` also get a **nested type check** covering the full declared structure.

:::note
For file servers with `format: csv`, `json`, or `avro` **no type check is generated at all** — the file is read *as* the contract's types, so a mismatch surfaces as a read error instead. `format: json` is additionally validated against a JSON Schema derived from the contract. See [Data Source Reference](./reference/index.md#how-data-types-work) for the full type-mapping rules.
:::

## Required, unique, and primary keys

```yaml
properties:
  - name: order_id
    primaryKey: true
  - name: external_ref
    unique: true
  - name: order_status
    required: true
```

- **`required: true`** → no missing values.
- **`unique: true`** → no duplicate values.
- **`primaryKey: true`** → both of the above. Declaring `required` or `unique` alongside it does not duplicate the check.

A **composite primary key** — several properties with `primaryKey: true` — is treated as a key over the tuple, not column by column. Each member gets its own not-null check, and the combination gets a single uniqueness check. Use `primaryKeyPosition` to order the members:

```yaml
properties:
  - name: order_id
    primaryKey: true
    primaryKeyPosition: 1
  - name: line_number
    primaryKey: true
    primaryKeyPosition: 2
```

> Produces: `order_id` not null, `line_number` not null, and `(order_id, line_number)` unique.

## Value constraints

`logicalTypeOptions` turns into value checks that behave identically on every backend — the CLI compiles each into dialect-specific SQL.

```yaml
properties:
  - name: order_total
    logicalType: integer
    logicalTypeOptions:
      minimum: 0
      maximum: 1000000
  - name: country_code
    logicalType: string
    logicalTypeOptions:
      minLength: 2
      maxLength: 2
      pattern: '^[A-Z]{2}$'
  - name: order_status
    logicalType: string
    logicalTypeOptions:
      enum: ['pending', 'shipped', 'delivered']
  - name: tags
    logicalType: array
    items:
      logicalType: string
    logicalTypeOptions:
      minItems: 1
      maxItems: 10
      uniqueItems: true
```

| Option | Fails when a value is… |
|---|---|
| `minLength` / `maxLength` | shorter / longer than the bound |
| `minimum` / `maximum` | below / above the bound (the bound itself passes) |
| `exclusiveMinimum` / `exclusiveMaximum` | below / above **or equal to** the bound |
| `pattern` | not matching the regular expression |
| `enum` | not one of the listed values |
| `minItems` / `maxItems` | an array with fewer / more elements than the bound |
| `uniqueItems` | an array that repeats an element |

`exclusiveMinimum` and `exclusiveMaximum` each produce two checks — a bound check and an inequality check — so a violation of either is reported separately.

## What is not checked

These are common sources of confusion. They are valid ODCS and appear in exports, but they generate no check:

- **`isNullable`** — the CLI reads `required`, not `isNullable`. Write `required: true` to assert that a column has no nulls.
- **`logicalTypeOptions.format`** — never enforced, on any property. On a `string` property (`email`, `uuid`, `uri`, …) use `pattern` for an enforceable equivalent. On a `date`, `timestamp` or `time` property `format` holds a date pattern such as `yyyy-MM-dd`, and `pattern` is *not* an equivalent there: by the time a check runs, the column has already been parsed as a date, so there is no string left to match. Such a column is validated as a date, in whatever format the server stores it.
- **Descriptive attributes** — `description`, `businessName`, `examples`, `tags`, `classification`, `criticalDataElement`, `transformSourceObjects`, and `customProperties`. `authoritativeDefinitions` generates no check either, but it *is* resolved and inlined before the checks are built — see [Link your Semantics](./semantics.md).
- **Schema-level attributes** other than `name`, `physicalName`, `properties`, and `quality`.

Anything beyond this list that you want verified belongs in a [quality rule](./quality-rules/index.md) — a `type: library` metric for the common cases, or `type: sql` for arbitrary expressions.

## Next steps

- Add rules that go beyond structure: **[Define your Quality Rules](./quality-rules/index.md)**.
- Declare freshness and retention promises: **[Define your Service Levels](./service-levels.md)**.
- Link a property to a shared business term instead of repeating it: **[Link your Semantics](./semantics.md)**.
- Generate a schema block from an existing table instead of writing it by hand: **[Imports](./imports/index.md)**.
