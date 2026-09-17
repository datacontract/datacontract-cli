---
sidebar_position: 7
title: "Azure Blob / ADLS"
description: "Create a data contract from files on Azure Blob storage or ADLS Gen2 and test them against it."
---

# <img className="page-icon" src="/img/icons/azure.svg" alt="" /> Azure Blob / ADLS

Test data stored in Azure Blob storage or Azure Data Lake Storage Gen2 (ADLS) in various formats.

## 1. Install

```bash
uv tool install --python python3.11 --upgrade 'datacontract-cli[azure]'
```

See [Installation](../installation.md) for pip, pipx, and Docker.

## 2. Authenticate

Authentication uses an Azure Service Principal (App Registration) with a secret. Create a `.env` file in your working directory (or export the variables):

```bash
# .env
DATACONTRACT_AZURE_TENANT_ID=79f5b80f-10ff-40b9-9d1f-774b42d605fc
DATACONTRACT_AZURE_CLIENT_ID=3cf7ce49-e2e9-4cbc-a922-4328d4a58622
DATACONTRACT_AZURE_CLIENT_SECRET=yZK8Q~GWO1MMXXXXXXXXXXXXX
```

## 3. Create a contract from your files

Import the schema straight from the container. This also generates a ready-to-test `servers` block:

```bash
datacontract import adls \
  --source abfss://my-container/orders/*.json \
  --output datacontract.yaml
```

The format is taken from the file suffix; pass `--format` for Delta tables, which have none.

## 4. Test the actual data

```bash
datacontract test datacontract.yaml
```

```
Testing datacontract.yaml
Server: production (type=azure, format=parquet, location=abfss://my-container/orders/*.parquet)
╭────────┬─────────────────────────────────────────────────┬─────────────────┬─────────╮
│ Result │ Check                                           │ Field           │ Details │
├────────┼─────────────────────────────────────────────────┼─────────────────┼─────────┤
│ passed │ Check that field 'order_id' is present          │ orders.order_id │         │
│ passed │ Check that field order_id has no missing values │ orders.order_id │         │
│  ...   │                                                 │                 │         │
╰────────┴─────────────────────────────────────────────────┴─────────────────┴─────────╯
🟢 data contract is valid. Run 24 checks. Took 4.5 seconds.
```

## 5. Let it catch a violation

The contract becomes valuable when it detects drift. Tighten an expectation — for example, mark a field as `required: true` that occasionally arrives empty, or add a quality rule:

```yaml
schema:
  - name: inventory_events
    # ...
    quality:
      - type: sql
        description: No event has a negative quantity
        query: SELECT COUNT(*) FROM inventory_events WHERE quantity < 0
        mustBe: 0
```

Run `datacontract test datacontract.yaml` again: every violation is listed as an error, and the command exits with code `1` — ready for [CI/CD and scheduled runs](../scheduling/index.md) so you catch drift before your consumers do.

## Reference

All authentication options (service principal, connection string, account key), supported location URL formats, and the data type handling per file format: **[Azure Reference](../reference/azure.md)**.

## Troubleshooting

- **`AuthorizationPermissionMismatch` / `403`** — the service principal needs the **Storage Blob Data Reader** role on the container or storage account (IAM role assignment, not just API permissions).
- **`No files found that match the pattern`** — check the `location` URL format (see below) and the glob; it matches blob names under the prefix.

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

The metadata-check path also accepts `DATACONTRACT_AZURE_CONNECTION_STRING` or `DATACONTRACT_AZURE_STORAGE_ACCOUNT_KEY` instead of the service principal variables.
