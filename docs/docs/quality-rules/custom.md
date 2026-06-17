---
sidebar_position: 4
title: "Custom Quality Rules"
description: "Engine-specific quality checks expressed in the native syntax of an engine such as DQX, SodaCL, or Great Expectations."
---

# Custom Quality Rules

A `type: custom` rule carries a check written in the **native syntax of a specific quality engine**. You name the engine with `engine` and provide the engine-specific definition under `implementation`. Custom rules let you use capabilities of an engine that the portable [library](./library.md) and [SQL](./sql.md) rules don't cover.

Custom rules are consumed by the matching engine — typically via the corresponding [exporter](../exports/index.md) — rather than being compiled to portable SQL.

## Databricks DQX

```yaml
schema:
  - name: events
    properties:
      - name: event_type
        logicalType: string
        quality:
          - type: custom
            engine: dqx
            implementation:
              criticality: error
              check:
                function: is_in_list
                arguments:
                  allowed:
                    - click
                    - view
                    - purchase
```

Export these to a DQX check file with [`datacontract export dqx`](../exports/dqx.md).

## SodaCL

```yaml
schema:
  - name: orders
    quality:
      - type: custom
        engine: soda
        implementation: |
          checks for orders:
            - row_count > 10
```

Export to a SodaCL file with [`datacontract export sodacl`](../exports/sodacl.md).

:::warning
Raw SodaCL custom checks (`type: custom`, `engine: soda`) are **no longer executed** by `datacontract test` since `soda-core` was removed; such a rule is reported as a warning. Migrate it to a [SQL rule](./sql.md) (`type: sql`) to keep it executable, or keep it as a custom rule purely for the SodaCL export.
:::

## Other engines

The same pattern applies to other engines (for example Great Expectations). Provide `engine` and an `implementation` understood by that engine, and use the matching [exporter](../exports/index.md) to generate its native artifact.
