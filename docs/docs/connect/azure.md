---
sidebar_position: 5
title: "Azure Blob / ADLS"
description: "Test data on Azure Blob storage or Azure Data Lake Storage Gen2."
---

<img className="page-icon" src="/img/icons/azure.svg" alt="" />

# Azure Blob / ADLS

:::info[Required extra]
This connection requires the `azure` and `duckdb` extras. See [Installation](../installation.md).
:::

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

## Metadata checks

Instead of reading the file contents, you can validate the metadata of the blobs themselves
(size, content type, last modified, file count, …). Each ODCS schema object with
`physicalType: file` represents a **unique folder/prefix** in Azure Blob storage or ADLS Gen2.
Its `properties` map directly to `BlobProperties` attributes from the Azure SDK: for every
declared property the engine extracts the corresponding attribute from each blob and validates
it against the quality constraints declared on that property.

| Property name | `BlobProperties` attribute |
|---|---|
| `name` | `blob.name` |
| `size` | `blob.size` |
| `lastModified` | `blob.last_modified` (UTC datetime) |
| `creationTime` | `blob.creation_time` (UTC datetime) |
| `lastAccessedOn` | `blob.last_accessed_on` (UTC datetime) |
| `contentType` | `blob.content_settings.content_type` |
| `contentEncoding` | `blob.content_settings.content_encoding` |
| `contentLanguage` | `blob.content_settings.content_language` |
| `contentDisposition` | `blob.content_settings.content_disposition` |
| `cacheControl` | `blob.content_settings.cache_control` |
| `contentMd5` | `blob.content_settings.content_md5` |
| `etag` | `blob.etag` |
| `blobType` | `blob.blob_type.value` (e.g. `BlockBlob`) |
| `blobTier` | `blob.blob_tier.value` (e.g. `Hot`) |
| `archiveStatus` | `blob.archive_status` |
| `serverEncrypted` | `blob.server_encrypted` |
| `deleted` | `blob.deleted` |
| `snapshotId` | `blob.snapshot` |
| `versionId` | `blob.version_id` |
| `tagCount` | `blob.tag_count` |

Schema-level quality checks (`schema.quality`) on the `rowCount` metric are evaluated as
**file-count** thresholds against the total number of blobs found under the prefix.

`contentType` is normalised before comparison: MIME parameters are stripped, so
`application/json; charset=utf-8` matches `application/json`.

Supported `location` URL formats (on the server block):

- `https://<account>.blob.core.windows.net/<container>/<prefix>`
- `abfss://<container>@<account>.dfs.core.windows.net/<prefix>`
- `azure://<container>@<account>.blob.core.windows.net/<prefix>`
- `wasbs://<container>@<account>.blob.core.windows.net/<prefix>`

