---
sidebar_position: 2
title: "Export: SQL Query"
description: "Export a data contract to a SQL SELECT query."
---

<img className="page-icon" src="/img/icons/database.svg" alt="" />

# Export: SQL Query

Exports a data contract to a SQL `SELECT` query over the contract's fields.

```bash
datacontract export sql-query orders.odcs.yaml --schema-name orders
```

Running this against the [example `orders` contract](https://github.com/datacontract/datacontract-cli/blob/main/examples/orders/orders.odcs.yaml) produces:

```sql
-- Data Contract: urn:datacontract:checkout:orders
-- SQL Dialect: snowflake
select
    order_id,
    order_timestamp,
    customer_id,
    order_total,
    status
from orders
```
