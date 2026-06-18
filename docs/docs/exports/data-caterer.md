---
sidebar_position: 24
title: "Export: Data Caterer"
description: "Export a data contract to a Data Caterer data-generation task."
---

<img className="page-icon" src="/img/icons/generic.svg" alt="" />

# Export: Data Caterer

Converts the data contract to a data-generation task in YAML that can be ingested by [Data Caterer](https://github.com/data-catering/data-caterer). This lets you generate production-like data in any environment based on your contract.

```bash
datacontract export data-caterer orders.odcs.yaml
```

Running this against the [example `orders` contract](https://github.com/datacontract/datacontract-cli/blob/main/examples/orders/orders.odcs.yaml) produces:

```yaml
name: Orders
steps:
- name: orders
  type: snowflake
  options: {}
  fields:
  - name: order_id
    type: string
    options:
      isUnique: true
      isPrimaryKey: true
  - name: order_timestamp
    type: timestamp
  - name: customer_id
    type: string
  - name: order_total
    type: double
  - name: status
    type: string
- name: line_items
  type: snowflake
  options: {}
  fields:
  - name: line_item_id
    type: string
    options:
      isUnique: true
      isPrimaryKey: true
  - name: order_id
    type: string
  - name: sku
    type: string
  - name: quantity
    type: integer
```

You can further customize generation by adding [additional metadata in the YAML](https://data.catering/setup/generator/data-generator/).
