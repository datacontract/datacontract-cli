---
sidebar_position: 5
title: "Azure Blob / ADLS"
description: "Test data on Azure Blob storage or Azure Data Lake Storage Gen2."
---

# Azure Blob / ADLS

Test data stored in Azure Blob storage or Azure Data Lake Storage Gen2 (ADLS) in various formats.

## Server

```yaml
servers:
  - server: production
    type: azure
    location: abfss://datameshdatabricksdemo.dfs.core.windows.net/inventory_events/*.parquet
    format: parquet
```

## Environment variables

Authentication uses an Azure Service Principal (App Registration) with a secret.

| Variable | Example | Description |
|---|---|---|
| `DATACONTRACT_AZURE_TENANT_ID` | `79f5b80f-...` | The Azure Tenant ID |
| `DATACONTRACT_AZURE_CLIENT_ID` | `3cf7ce49-...` | The Application/Client ID of the app registration |
| `DATACONTRACT_AZURE_CLIENT_SECRET` | `yZK8Q~GWO1M...` | The client secret value |

Requires the `azure` / `duckdb` extra.
