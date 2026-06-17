---
sidebar_position: 6
title: "Import: BigQuery"
description: "Create a data contract from BigQuery, via an exported JSON file or the BigQuery API."
---

# Import: BigQuery

Creates a data contract from BigQuery, either from an exported table definition (JSON file) or directly from the BigQuery API.

```bash
# From a BigQuery JSON file
datacontract import bigquery --source bigquery_table.json

# From the BigQuery API, specifying tables
datacontract import bigquery --bigquery-project my-project --bigquery-dataset my_dataset \
  --bigquery-table orders --bigquery-table line_items

# From the BigQuery API, all tables in the dataset
datacontract import bigquery --bigquery-project my-project --bigquery-dataset my_dataset
```
