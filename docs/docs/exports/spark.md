---
sidebar_position: 19
title: "Export: Spark"
description: "Export a data contract to a Spark StructType schema."
---

<img className="page-icon" src="/img/icons/database.svg" alt="" />

# Export: Spark

Converts the data contract into a Spark `StructType` schema. The returned value is Python code representing the model schemas.

```bash
datacontract export spark datacontract.yaml
```

For Spark data types, see the [Spark documentation](https://spark.apache.org/docs/latest/sql-ref-datatypes.html).
