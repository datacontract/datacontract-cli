---
sidebar_position: 19
title: "Export: Spark"
description: "Export a data contract to a Spark StructType schema."
---

<img className="page-icon" src="/img/icons/database.svg" alt="" />

# Export: Spark

Converts the data contract into a Spark `StructType` schema. The returned value is Python code representing the model schemas.

```bash
datacontract export spark orders.odcs.yaml
```

Running this against the [example `orders` contract](https://github.com/datacontract/datacontract-cli/blob/main/examples/orders/orders.odcs.yaml) produces (excerpt):

```python
orders = StructType([
    StructField("order_id",
        StringType(),
        False,
        {"comment": "Unique identifier of the order."}
    ),
    StructField("order_timestamp",
        TimestampType(),
        False,
        {"comment": "Timestamp when the order was placed."}
    ),
    StructField("customer_id",
        StringType(),
        False,
        {"comment": "Reference to the customer who placed the order."}
    ),
    StructField("order_total",
        DecimalType(10, 0),
        False,
        {"comment": "Total amount of the order in cents."}
    ),
    StructField("status",
        StringType(),
        False,
        {"comment": "Current fulfilment status of the order."}
    )
])

line_items = StructType([
    StructField("line_item_id",
        StringType(),
        False,
        {"comment": "Unique identifier of the line item."}
    ),
# …
```

For Spark data types, see the [Spark documentation](https://spark.apache.org/docs/latest/sql-ref-datatypes.html).
