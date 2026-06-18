---
sidebar_position: 11
title: "Export: ODCS"
description: "Export a data contract to the Open Data Contract Standard (ODCS) format."
---

<img className="page-icon" src="/img/icons/generic.svg" alt="" />

# Export: ODCS

Exports the data contract to the [Open Data Contract Standard](../open-data-contract-standard.md) (ODCS) YAML format. Useful for normalizing or converting an in-memory contract back to canonical ODCS.

```bash
datacontract export odcs orders.odcs.yaml --output orders.normalized.yaml
```

Running this against the [example `orders` contract](https://github.com/datacontract/datacontract-cli/blob/main/examples/orders/orders.odcs.yaml) produces (excerpt):

```yaml
version: 1.0.0
kind: DataContract
apiVersion: v3.1.0
id: urn:datacontract:checkout:orders
name: Orders
tags:
- checkout
- orders
status: active
servers:
- server: production
  type: snowflake
  account: my-account
  database: ANALYTICS
  schema: ORDERS
- server: bigquery
  type: bigquery
  dataset: orders
  project: my-gcp-project
description:
  usage: Used by the analytics team to build revenue dashboards and by finance for
    reconciliation.
  purpose: Tracks customer orders and their line items for analytics and reporting.
  limitations: Not suitable for real-time fraud detection; data is loaded in hourly
    batches.
schema:
- name: orders
  physicalType: table
  description: One row per customer order.
  physicalName: orders
  properties:
  - name: order_id
# …
```
