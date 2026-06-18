---
sidebar_position: 3
title: "Text Quality Rules"
description: "A human-readable quality expectation captured for documentation, not executed automatically."
---

# Text Quality Rules

A `type: text` rule is a **human-readable expectation** written in plain language. It is **not executed** by `datacontract test` — it documents an agreement or an expectation that cannot (yet) be automated, so it stays visible in the contract and in generated documentation.

```yaml
schema:
  - name: orders
    properties:
      - name: order_status
        logicalType: string
        quality:
          - type: text
            description: >
              order_status transitions follow the lifecycle
              placed → shipped → delivered, and never moves backwards.
```

## When to use it

- The expectation is understood and agreed, but you don't (yet) have a query or metric for it.
- The rule is enforced by an external process and you want to record it in the contract.
- You want to communicate intent to consumers alongside the executable rules.

When you are ready to enforce it automatically, promote it to a [SQL](./sql.md) or [library](./library.md) rule.
