---
sidebar_position: 2
title: "Amazon Redshift"
description: "Test data in Amazon Redshift."
---

<img className="page-icon" src="/img/icons/redshift.svg" alt="" />

# Amazon Redshift

Test data in Amazon Redshift (both provisioned clusters and Redshift Serverless). Redshift is reached over the PostgreSQL wire protocol via the ibis Postgres backend, using username/password authentication.

## Server

```yaml
servers:
  - server: redshift
    type: redshift
    host: my-workgroup.123456789012.us-east-1.redshift-serverless.amazonaws.com
    port: 5439
    database: dev
    schema: analytics
```

## Environment variables

| Connection parameter | Environment variable |
|---|---|
| `user` | `DATACONTRACT_REDSHIFT_USERNAME` |
| `password` | `DATACONTRACT_REDSHIFT_PASSWORD` |

:::note
IAM-based authentication (region / access key / role ARN) is not currently supported for Redshift, because ibis connects through the generic Postgres backend rather than a Redshift-specific driver.
:::

Requires the `redshift` extra.
