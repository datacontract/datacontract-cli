---
sidebar_position: 17
title: "Export: DBML"
description: "Export a data contract to DBML (Database Markup Language) for diagrams and documentation."
---

<img className="page-icon" src="/img/icons/database.svg" alt="" />

# Export: DBML

Converts the data contract to [DBML](https://dbml.dbdiagram.io/) (Database Markup Language).

```bash
datacontract export dbml orders.odcs.yaml --output orders.dbml
```

Running this against the [example `orders` contract](https://github.com/datacontract/datacontract-cli/blob/main/examples/orders/orders.odcs.yaml) produces:

```text
/*
Generated at Jun 18 2026 by datacontract-cli version 1.0.1
for datacontract Orders (urn:datacontract:checkout:orders) version 1.0.0
Using Logical Datacontract Types for the field types
*/
Project "Orders" {
    note: '''Tracks customer orders and their line items for analytics and reporting.'''
}

Table orders {
    note: "One row per customer order."
    order_id string [pk, unique, not null, note: "Unique identifier of the order."]
    order_timestamp date [not null, note: "Timestamp when the order was placed."]
    customer_id string [not null, note: "Reference to the customer who placed the order."]
    order_total number [not null, note: "Total amount of the order in cents."]
    status string [not null, note: "Current fulfilment status of the order."]
}

Table line_items {
    note: "One row per line item within an order."
    line_item_id string [pk, unique, not null, note: "Unique identifier of the line item."]
    order_id string [not null, note: "Reference to the parent order."]
    sku string [not null, note: "Stock keeping unit of the purchased product."]
    quantity integer [not null, note: "Number of units purchased."]
}
```

If a server is selected via `--server`, the logical data types are converted to that database's specific types (based on the server `type`). If no server is selected, the logical data types are exported.
