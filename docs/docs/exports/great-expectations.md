---
sidebar_position: 23
title: "Export: Great Expectations"
description: "Export a data contract to a Great Expectations suite."
---

<img className="page-icon" src="/img/icons/generic.svg" alt="" />

# Export: Great Expectations

Transforms a data contract into a comprehensive [Great Expectations](https://greatexpectations.io/) JSON suite. If the contract includes multiple models, specify the model with `--schema-name`.

```bash
datacontract export great-expectations orders.odcs.yaml --schema-name orders
```

Running this against the [example `orders` contract](https://github.com/datacontract/datacontract-cli/blob/main/examples/orders/orders.odcs.yaml) produces (excerpt):

```json
{
  "name": "orders.1.0.0",
  "expectations": [
    {
      "type": "expect_table_columns_to_match_ordered_list",
      "kwargs": {
        "column_list": [
          "order_id",
          "order_timestamp",
          "customer_id",
          "order_total",
          "status"
        ]
      },
      "meta": {}
    },
    {
      "type": "expect_column_values_to_be_of_type",
      "kwargs": {
        "column": "order_id",
        "type_": "VARCHAR"
      },
      "meta": {}
    },
    {
      "type": "expect_column_values_to_be_unique",
      "kwargs": {
        "column": "order_id"
      },
      "meta": {}
    },
    // … one expectation per field and quality rule
  ]
}
```

The export builds expectations from the model definition (with a fixed mapping) and from the `quality` rules of each model (see the [expectations gallery](https://greatexpectations.io/expectations/)).

## Additional options

- `suite_name` — the name of the expectation suite. Defaults to a name derived from the model name(s).
- `engine` — the execution engine: `pandas` (in-memory dataframes), `spark` (Spark dataframes), or `sql` (SQL databases).
- `sql_server_type` — the SQL server type to connect with when `engine` is `sql`. Ensures the correct SQL dialect and connection settings are applied.
