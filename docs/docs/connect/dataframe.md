---
sidebar_position: 17
title: "Spark DataFrame"
description: "Test in-memory Spark DataFrames in a pipeline (programmatic)."
---

<img className="page-icon" src="/img/icons/spark.svg" alt="" />

# Spark DataFrame

:::info[Required extra]
This connection needs **no additional extra**. See [Installation](../installation.md).
:::

Test Spark DataFrames in a pipeline before writing them to a data source. DataFrames are registered as named temporary views; multiple views are supported if the contract has multiple schemas.

## Server

```yaml
servers:
  - server: production
    type: dataframe
```

## Programmatic use

```python
from datacontract.data_contract import DataContract

df.createOrReplaceTempView("my_table")

data_contract = DataContract(
  data_contract_file="datacontract.yaml",
  spark=spark,
)
run = data_contract.test()
assert run.result == "passed"
```

