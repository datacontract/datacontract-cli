---
sidebar_position: 6
title: "Import: Azure Blob Storage"
description: "Create a data contract from files in Azure Blob Storage."
---

# <img className="page-icon" src="/img/icons/azure.svg" alt="" /> Import: Azure Blob Storage

Creates a data contract from files in Azure Blob Storage, in CSV, JSON, Parquet, or Delta format.

```bash
datacontract import azure \
  --source abfss://my-container/orders/*.json \
  --output datacontract.yaml
```

The format is taken from the file suffix; pass `--format` for Delta tables, which have none, or to override the guess. `--delimiter` pins how a JSON file is laid out (`new_line`, `array`, or `none`) instead of letting it be detected.

The objects are read with duckdb through the same connection the test path uses, so the import authenticates identically and infers the column types from exactly the reader that later verifies them.

The generated contract includes a ready-to-test `servers` block, so you can run `datacontract test datacontract.yaml` immediately afterwards — see the **[Azure Blob Storage connection guide](../testing/azure.md)** for the full 5-minute walkthrough and troubleshooting.

Credentials are the same ones `datacontract test` uses — see the [Azure Blob Storage Reference](../reference/azure.md).
