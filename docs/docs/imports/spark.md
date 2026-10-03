---
sidebar_position: 30
title: "Import: Spark"
description: "Create a data contract from Spark tables or DataFrames (programmatic)."
---

# <img className="page-icon" src="/img/icons/spark.svg" alt="" /> Import: Spark

Creates a data contract from a Spark schema. This importer is typically used programmatically from within a Spark context.

It needs PySpark, which the CLI does not install (you supply the Spark session), and the `databricks` extra:

```bash
pip install pyspark 'datacontract-cli[databricks]'
```

Import tables or views registered in the current Spark session:

```bash
datacontract import spark --tables orders,line_items --output datacontract.yaml
```

Or import a DataFrame from Python, naming the schema with `source`:

```python
from datacontract.data_contract import DataContract

odcs = DataContract.import_from_source("spark", source="orders", dataframe=df)
```

A table description can be supplied alongside the table or dataframe to enrich the generated contract.

All options: **[`datacontract import spark`](../commands/import/spark.md)**.
