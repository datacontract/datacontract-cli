---
sidebar_position: 10
title: "Export: Protobuf"
description: "Export a data contract to a Protobuf schema."
---

<img className="page-icon" src="/img/icons/generic.svg" alt="" />

# Export: Protobuf

Converts the data contract to a [Protocol Buffers](https://protobuf.dev/) schema.

```bash
datacontract export protobuf orders.odcs.yaml --output orders.proto
```

Running this against the [example `orders` contract](https://github.com/datacontract/datacontract-cli/blob/main/examples/orders/orders.odcs.yaml) produces:

```protobuf
syntax = "proto3";

package example;

// One row per customer order.
message Orders {
  // Unique identifier of the order.
  string order_id = 1;
  // Timestamp when the order was placed.
  string order_timestamp = 2;
  // Reference to the customer who placed the order.
  string customer_id = 3;
  // Total amount of the order in cents.
  double order_total = 4;
  // Current fulfilment status of the order.
  string status = 5;
}

// One row per line item within an order.
message LineItems {
  // Unique identifier of the line item.
  string line_item_id = 1;
  // Reference to the parent order.
  string order_id = 2;
  // Stock keeping unit of the purchased product.
  string sku = 3;
  // Number of units purchased.
  int32 quantity = 4;
}
```
