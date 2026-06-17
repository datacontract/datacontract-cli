---
sidebar_position: 14
title: "Import: Spark"
description: "Create a data contract from Spark tables or DataFrames (programmatic)."
---

# Import: Spark

Creates a data contract from a Spark schema. This importer is typically used programmatically from within a Spark context.

```python
# Import table(s) from the Spark context
datacontract import spark --source orders,line_items

# Import a single table
datacontract import spark --source orders

# Import a Spark dataframe (programmatic)
# data_contract = DataContract().import_from_source("spark", dataframe=df)
```

A table description can be supplied alongside the table or dataframe to enrich the generated contract.
