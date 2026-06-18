---
sidebar_position: 16
title: "Export: BigQuery"
description: "Export a data contract to a BigQuery schema."
---

<img className="page-icon" src="/img/icons/bigquery.svg" alt="" />

# Export: BigQuery

Converts the data contract to a [BigQuery table schema](https://cloud.google.com/bigquery/docs/schemas) JSON.

```bash
datacontract export bigquery orders.odcs.yaml --schema-name orders --server bigquery --output orders.bigquery.json
```

Running this against the [example `orders` contract](https://github.com/datacontract/datacontract-cli/blob/main/examples/orders/orders.odcs.yaml) produces (excerpt):

```json
{
  "kind": "bigquery#table",
  "tableReference": {
    "datasetId": "orders",
    "projectId": "my-gcp-project",
    "tableId": "orders"
  },
  "description": "One row per customer order.",
  "schema": {
    "fields": [
      {
        "name": "order_id",
        "type": "STRING",
        "mode": "REQUIRED",
        "description": "Unique identifier of the order.",
        "maxLength": null
      },
      {
        "name": "order_timestamp",
        "type": "TIMESTAMP",
        "mode": "REQUIRED",
        "description": "Timestamp when the order was placed."
      },
      {
        "name": "customer_id",
        "type": "STRING",
        "mode": "REQUIRED",
        "description": "Reference to the customer who placed the order.",
        "maxLength": null
      },
      // … remaining fields: order_total, status
    ]
  }
}
```
