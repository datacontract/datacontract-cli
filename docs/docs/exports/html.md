---
sidebar_position: 13
title: "Export: HTML"
description: "Export a data contract to a standalone HTML page."
---

<img className="page-icon" src="/img/icons/generic.svg" alt="" />

# Export: HTML

Generates a standalone, self-contained HTML page documenting the data contract.

```bash
datacontract export html orders.odcs.yaml --output orders.html
```

Running this against the [example `orders` contract](https://github.com/datacontract/datacontract-cli/blob/main/examples/orders/orders.odcs.yaml) produces a single self-contained `orders.html` file (no external assets) that renders:

- the contract metadata (name, version, status, description),
- each schema (`orders`, `line_items`) as a table of fields with their types, constraints, and descriptions,
- the configured servers, quality checks, and service-level properties.

Open the file in any browser or publish it as static documentation.
