---
sidebar_position: 6
title: "Export: Avro"
description: "Export a data contract to an Avro schema, with custom logicalType and default support."
---

<img className="page-icon" src="/img/icons/generic.svg" alt="" />

# Export: Avro

Converts the data contract into an Avro schema. It supports specifying custom Avro properties for logical types and default values.

```bash
datacontract export avro orders.odcs.yaml --schema-name orders --output orders.avsc
```

Running this against the [example `orders` contract](https://github.com/datacontract/datacontract-cli/blob/main/examples/orders/orders.odcs.yaml) produces:

```json
{
  "type": "record",
  "name": "orders",
  "doc": "One row per customer order.",
  "fields": [
    {
      "name": "order_id",
      "doc": "Unique identifier of the order.",
      "type": "string"
    },
    {
      "name": "order_timestamp",
      "doc": "Timestamp when the order was placed.",
      "type": {
        "type": "int",
        "logicalType": "date"
      }
    },
    {
      "name": "customer_id",
      "doc": "Reference to the customer who placed the order.",
      "type": "string"
    },
    {
      "name": "order_total",
      "doc": "Total amount of the order in cents.",
      "type": "bytes"
    },
    {
      "name": "status",
      "doc": "Current fulfilment status of the order.",
      "type": "string"
    }
  ]
}
```

## Custom Avro properties

A **`config` map on property level** may include additional key-value pairs. At the moment, [`logicalType`](https://avro.apache.org/docs/1.11.0/spec.html#Logical+Types) and `default` are supported.

```yaml
schema:
  - name: orders
    properties:
      - name: my_field_1
        description: Example for AVRO with Timestamp (microsecond precision)
        logicalType: integer
        physicalType: long
        examples:
          - 1672534861000000  # 2023-01-01 01:01:01 in microseconds
        required: true
        config:
          avroLogicalType: local-timestamp-micros
          avroDefault: 1672534861000000
```

- `avroLogicalType` — the Avro logical type of the property (here `local-timestamp-micros`).
- `avroDefault` — the default value for the property in Avro.
