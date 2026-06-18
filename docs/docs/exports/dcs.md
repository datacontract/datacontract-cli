---
sidebar_position: 25
title: "Export: DCS"
description: "Export a data contract to the DCS format."
---

<img className="page-icon" src="/img/icons/generic.svg" alt="" />

# Export: DCS

Exports the data contract to the DCS (Data Contract Specification) format.

```bash
datacontract export dcs orders.odcs.yaml --output datacontract.yaml
```

Running this against the [example `orders` contract](https://github.com/datacontract/datacontract-cli/blob/main/examples/orders/orders.odcs.yaml) produces (excerpt):

```yaml
id: urn:datacontract:checkout:orders
info:
  title: Orders
  version: 1.0.0
  status: active
  description: Tracks customer orders and their line items for analytics and reporting.
servers:
  production:
    type: snowflake
    account: my-account
    database: ANALYTICS
    schema: ORDERS
  bigquery:
    type: bigquery
    project: my-gcp-project
    dataset: orders
terms:
  usage: Used by the analytics team to build revenue dashboards and by finance for
    reconciliation.
  limitations: Not suitable for real-time fraud detection; data is loaded in hourly
    batches.
  description: Tracks customer orders and their line items for analytics and reporting.
models:
  orders:
    description: One row per customer order.
    type: table
    fields:
      order_id:
        type: string
        required: true
        primaryKey: true
        unique: true
        description: Unique identifier of the order.
      order_timestamp:
# …
```
