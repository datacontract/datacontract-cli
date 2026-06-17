---
sidebar_position: 7
title: "Google BigQuery"
description: "Test data in Google BigQuery tables and views."
---

# Google BigQuery

Test data in Google BigQuery. Authentication uses a Service Account Key or Application Default Credentials (ADC) — including Workload Identity Federation (WIF), the GCE metadata server, and `gcloud auth application-default login`. The service account should have the **BigQuery Job User** and **BigQuery Data Viewer** roles.

When `DATACONTRACT_BIGQUERY_ACCOUNT_INFO_JSON_PATH` is not set, the CLI falls back to ADC automatically.

## Example

```yaml
servers:
  production:
    type: bigquery
    project: datameshexample-product
    dataset: datacontract_cli_test_dataset
models:
  datacontract_cli_test_table: # corresponds to a BigQuery table
    type: table
    fields: ...
```

## Environment variables

| Variable | Example | Description |
|---|---|---|
| `DATACONTRACT_BIGQUERY_ACCOUNT_INFO_JSON_PATH` | `~/service-access-key.json` | Service Account key JSON file. If unset, ADC/WIF is used. |
| `DATACONTRACT_BIGQUERY_IMPERSONATION_ACCOUNT` | `sa@project.iam.gserviceaccount.com` | Optional. Service account to impersonate (works with key file or ADC). |
| `DATACONTRACT_BIGQUERY_BILLING_PROJECT` | `my-compute-project` | Optional. Project to bill query jobs to. Requires `bigquery.jobUser` on the billing project and `bigquery.dataViewer` on the data project. |

Requires the `bigquery` extra.
