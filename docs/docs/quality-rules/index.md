---
sidebar_position: 0
title: "Define your Quality Rules"
slug: /quality-rules
description: "Define and run data quality rules in a data contract using ODCS quality checks: SQL, library, text, and custom."
---

# Define your Quality Rules

Beyond schema checks (presence, type, nullability), a data contract can declare **quality rules**. When you run [`datacontract test`](../testing.md), executable rules run against the data source and are reported alongside the schema checks.

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
    <img src="/img/icons/generic.svg" alt="" />
    <span><span className="doc-card-title">Library</span><span className="doc-card-desc">Predefined, portable checks such as rowCount, nullValues, and duplicateValues.</span></span>
  </a>
  <a className="doc-card" href="/quality-rules/text">
    <img src="/img/icons/generic.svg" alt="" />
    <span><span className="doc-card-title">Text</span><span className="doc-card-desc">A human-readable expectation, for documentation only.</span></span>
  </a>
  <a className="doc-card" href="/quality-rules/custom">
    <img src="/img/icons/custom.svg" alt="" />
    <span><span className="doc-card-title">Custom</span><span className="doc-card-desc">Engine-specific checks (e.g. DQX, SodaCL, Great Expectations).</span></span>
  </a>
</div>

## Running only quality checks

Use `--checks` to restrict a run to quality rules:

```bash
datacontract test --checks quality datacontract.yaml
```

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
