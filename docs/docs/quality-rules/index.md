---
sidebar_position: 0
title: "Define your Quality Rules"
slug: /quality-rules
description: "Define and run data quality rules in a data contract using ODCS quality checks: SQL, library, text, and custom."
---

# Define your Quality Rules

Beyond the [schema checks](../schema.md) (presence, type, `required`, `unique`, primary keys, value ranges), a data contract can declare **quality rules**. When you run [`datacontract test`](../testing/index.md), executable rules run against the data source and are reported alongside the schema checks.

Quality rules use the ODCS `quality` attribute, which can be attached either to a **schema** (table/object level) or to an individual **property** (column/field level):

```yaml
schema:
  - name: orders
    quality:                       # schema-level rule
      - type: library
        metric: rowCount
        mustBeGreaterThan: 0
    properties:
      - name: order_total
        quality:                   # property-level rule
          - type: library
            metric: nullValues
            mustBe: 0
```

## Quality rule types

ODCS defines four `type`s of quality rule. Each has its own page:

<div className="card-grid">
  <a className="doc-card" href="/quality-rules/sql">
    <img src="/img/icons/database.svg" alt="" />
    <span><span className="doc-card-title">SQL</span><span className="doc-card-desc">Run a custom SQL query and compare the result to a threshold.</span></span>
  </a>
  <a className="doc-card" href="/quality-rules/library">
    <img src="/img/icons/custom.svg" alt="" />
    <span><span className="doc-card-title">Library</span><span className="doc-card-desc">Predefined, portable checks such as rowCount, nullValues, and duplicateValues.</span></span>
  </a>
  <a className="doc-card" href="/quality-rules/text">
    <img src="/img/icons/custom.svg" alt="" />
    <span><span className="doc-card-title">Text</span><span className="doc-card-desc">A human-readable expectation, for documentation only.</span></span>
  </a>
  <a className="doc-card" href="/quality-rules/custom">
    <img src="/img/icons/database.svg" alt="" />
    <span><span className="doc-card-title">Custom</span><span className="doc-card-desc">Engine-specific checks (e.g. DQX, SodaCL, Great Expectations).</span></span>
  </a>
</div>

## Quality dimensions

Any rule can be classified with a `dimension` — the aspect of data quality it protects. It is optional and works with every rule type. It documents what the contract's quality coverage adds up to, and `datacontract test --dimension` runs one aspect at a time.

```yaml
schema:
  - name: orders
    quality:
      - type: library
        metric: rowCount
        mustBeGreaterThan: 0
        dimension: completeness
    properties:
      - name: order_id
        quality:
          - type: library
            metric: duplicateValues
            mustBe: 0
            dimension: uniqueness
```

ODCS defines seven dimensions. `datacontract lint` rejects any other value:

| Dimension | The data… |
|---|---|
| `accuracy` | correctly describes the real-world entity or event it represents |
| `completeness` | contains all the records and values that are expected |
| `conformity` | follows the agreed format, type, and set of allowed values |
| `consistency` | agrees with itself and with related data elsewhere |
| `coverage` | includes the full population it claims to describe |
| `timeliness` | is available and current when it is needed |
| `uniqueness` | contains no unintended duplicates |

The [HTML export](../exports/html.md) renders the dimension as a badge next to schema-level rules.

## Identifying rules

Any rule can carry an `id` and a list of `tags`. Both are optional and work with every rule type. They name a rule so that a pipeline can run it on its own: an `id` addresses exactly one rule, `tags` group rules that belong together — by cost, criticality, or the pipeline step they guard.

```yaml
schema:
  - name: orders
    quality:
      - id: orders_not_empty
        type: library
        metric: rowCount
        mustBeGreaterThan: 0
        tags: ["critical", "cheap"]
    properties:
      - name: order_id
        quality:
          - id: order_id_is_unique
            type: library
            metric: duplicateValues
            mustBe: 0
            tags: ["critical", "expensive"]
```

An `id` must be unique within the contract, so that `--quality-id` selects a single rule. Test results report the `id` and `tags` of the rule each check comes from.

## Running only quality checks

Use `--checks` to restrict a run to quality rules:

```bash
datacontract test --checks quality datacontract.yaml
```

Use `--dimension` to run one aspect of quality across the whole contract:

```bash
datacontract test --dimension uniqueness datacontract.yaml
datacontract test --dimension completeness,accuracy datacontract.yaml
```

This selects quality rules by their declared `dimension` **and** the built-in checks that measure the same thing — `--dimension uniqueness` runs your `duplicateValues` rules alongside the `unique` and primary-key checks derived from the schema.

Quality rules that declare no `dimension` are never selected: only the author can say what a custom rule measures. If nothing matches, the run executes nothing and reports no checks.

Use `--quality-id` to run a single rule, and `--tag` to run a group of them:

```bash
datacontract test --quality-id order_id_is_unique datacontract.yaml
datacontract test --tag critical datacontract.yaml
datacontract test --tag critical,cheap datacontract.yaml
```

Both select quality rules only — no schema or service level checks run alongside them. This makes it possible to spread the rules of one contract over a data pipeline: run the cheap rules on ingest, the expensive ones after the nightly load, without splitting the contract into several files.

`--quality-id` matches the `id` of the rule, and fails the run if no rule in the contract declares it — a mistyped id must not pass by testing nothing. `--tag` matches the `tags` of the rule (not the `tags` of a schema or property), and reports no checks when nothing matches. Options combine: `--tag critical --checks quality --server production` runs the critical rules on production.

### Dimensions of the built-in checks

[Schema checks](../schema.md) and [service levels](../service-levels.md) have no `dimension` field to set, so the CLI assigns each the dimension it measures:

| Dimension | Built-in checks |
|---|---|
| `completeness` | `required` fields, primary key not-null |
| `uniqueness` | `unique` fields, primary key uniqueness (including composite keys) |
| `conformity` | field presence, logical and physical types, nested types, `pattern`, `enum`, length and value bounds, JSON Schema validation, `slaProperties` retention |
| `timeliness` | `slaProperties` freshness |

## Where quality rules are used

Executable rules (`sql`, `library`) run during `test`. All rule types are also translated when you export to a quality engine:

- **[dbt](../dbt.md)** — rules become native dbt tests, with `dbt_utils` tests and singular SQL tests for rules that cannot be expressed natively.
- **[SodaCL](../exports/sodacl.md)** — rules become Soda checks.
- **[Great Expectations](../exports/great-expectations.md)** — rules become expectations in a suite.
- **[DQX](../exports/dqx.md)** — rules become Databricks DQX checks.

## Inspecting failing rows

When a quality (or schema) check fails, add `--include-failed-samples` to `test` to collect a small sample of the offending rows (identifier + offending columns; sensitive columns are omitted). This is off by default.

```bash
datacontract test --include-failed-samples datacontract.yaml
```

## Learn more

- The full quality syntax is part of the [Open Data Contract Standard](https://bitol-io.github.io/open-data-contract-standard/latest/).
- Promises about *when* the data arrives and how long it is kept are not quality rules — see [Define your Service Levels](../service-levels.md).
