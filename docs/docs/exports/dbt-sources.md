---
sidebar_position: 4
title: "Export: dbt Sources"
description: "Export a data contract to dbt sources YAML."
---

<img className="page-icon" src="/img/icons/generic.svg" alt="" />

# Export: dbt Sources

Converts the data contract to a dbt `sources` YAML definition.

```bash
datacontract export dbt-sources orders.odcs.yaml
```

Running this against the [example `orders` contract](https://github.com/datacontract/datacontract-cli/blob/main/examples/orders/orders.odcs.yaml) produces (excerpt):

```yaml
version: 2
sources:
- name: urn:datacontract:checkout:orders
  description: Tracks customer orders and their line items for analytics and reporting.
  tables:
  - name: orders
    description: One row per customer order.
    columns:
    - name: order_id
      data_tests:
      - not_null
      - unique
      data_type: VARCHAR
      description: Unique identifier of the order.
    - name: order_timestamp
      data_tests:
      - not_null
      data_type: TIMESTAMP_TZ
      description: Timestamp when the order was placed.
    - name: customer_id
      data_tests:
      - not_null
      data_type: VARCHAR
      description: Reference to the customer who placed the order.
    - name: order_total
      data_tests:
      - not_null
      data_type: NUMBER
      description: Total amount of the order in cents.
    - name: status
      data_tests:
      - not_null
      data_type: VARCHAR
      description: Current fulfilment status of the order.
  - name: line_items
    description: One row per line item within an order.
    columns:
    - name: line_item_id
      data_tests:
      - not_null
# …
```

As with [`dbt-models`](./dbt-models.md), selecting a server maps logical types to that server's data types; otherwise `snowflake` is used.
