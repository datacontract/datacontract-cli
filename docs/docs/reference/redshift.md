---
sidebar_position: 2
title: "Amazon Redshift Reference"
sidebar_label: "Amazon Redshift"
description: "All Redshift authentication options and data type mappings."
---

# <img className="page-icon" src="/img/icons/redshift.svg" alt="" /> Amazon Redshift Reference

Authentication options and data type handling for [Redshift connections](../testing/redshift.md).

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

## Authentication

`datacontract test` and `datacontract import redshift` authenticate identically. `host`, `port` (default 5439), `database`, and `schema` come from the contract's `servers` block, and can be overridden with `DATACONTRACT_REDSHIFT_HOST`, `DATACONTRACT_REDSHIFT_PORT`, `DATACONTRACT_REDSHIFT_DATABASE`, and `DATACONTRACT_REDSHIFT_SCHEMA`; for the import they are passed as `--source`, `--port`, `--database`, and `--schema`.

| Variable | Example | Description |
|---|---|---|
| `DATACONTRACT_REDSHIFT_AUTHENTICATION` | `iam` | `password` or `iam`; only needed to override what is inferred |
| `DATACONTRACT_REDSHIFT_USERNAME` | `awsuser` | Database user. Required for `password`; in `iam` mode it selects the legacy API (see below) |
| `DATACONTRACT_REDSHIFT_DB_USER` | `analytics_user` | Database user for `iam` mode only, taking precedence over `DATACONTRACT_REDSHIFT_USERNAME` |
| `DATACONTRACT_REDSHIFT_PASSWORD` | `mysecretpassword` | Password (`password` mode only) |
| `DATACONTRACT_REDSHIFT_SSLMODE` | `verify-full` | TLS mode passed to the driver. Defaults to `require` in `iam` mode, and to the driver's own default (`prefer`) otherwise |

### IAM authentication

The method is inferred: setting `DATACONTRACT_REDSHIFT_PASSWORD` selects a database login, otherwise resolvable AWS credentials select IAM. Set `DATACONTRACT_REDSHIFT_AUTHENTICATION` explicitly only to override that. With IAM, the CLI asks AWS for temporary database credentials and uses them to log in — no database password anywhere. The AWS credentials themselves come from the same variables Athena uses (`DATACONTRACT_S3_ACCESS_KEY_ID`, `DATACONTRACT_S3_SECRET_ACCESS_KEY`, `DATACONTRACT_S3_SESSION_TOKEN`, `DATACONTRACT_S3_REGION`), and fall back to the standard AWS chain: `aws sso login`, `AWS_PROFILE`, EC2/ECS/EKS instance roles, or GitHub OIDC in CI.

Which AWS API is called depends on the endpoint and whether a database user is set — either `DATACONTRACT_REDSHIFT_DB_USER` or, failing that, `DATACONTRACT_REDSHIFT_USERNAME`:

| Endpoint | Database user set | API |
|---|---|---|
| Serverless | — | `redshift-serverless:GetCredentials` |
| Provisioned | no | `redshift:GetClusterCredentialsWithIAM` — the database user is derived from your IAM identity |
| Provisioned | yes | `redshift:GetClusterCredentials` — credentials are requested for that database user |

Use `DATACONTRACT_REDSHIFT_DB_USER` when `DATACONTRACT_REDSHIFT_USERNAME` is already set for something else, such as a database login used by a different environment: it names the IAM database user explicitly, rather than inheriting a username that was never meant to select the legacy API.

The workgroup or cluster identifier and the region are derived from the endpoint host in the `servers` block, so a standard endpoint needs no extra configuration. Custom domains and VPC endpoints don't follow that naming, so they need an override:

| Variable | Example | Description |
|---|---|---|
| `DATACONTRACT_REDSHIFT_WORKGROUP` | `my-workgroup` | Serverless workgroup name |
| `DATACONTRACT_REDSHIFT_CLUSTER_IDENTIFIER` | `my-cluster` | Provisioned cluster identifier |
| `DATACONTRACT_REDSHIFT_REGION` | `eu-central-1` | AWS region (otherwise `DATACONTRACT_S3_REGION`, then the host) |
| `DATACONTRACT_REDSHIFT_DURATION_SECONDS` | `3600` | Lifetime of the temporary credentials (900–3600) |
| `DATACONTRACT_REDSHIFT_AUTO_CREATE` | `true` | Create the database user if it doesn't exist (`GetClusterCredentials` only) |
| `DATACONTRACT_REDSHIFT_DB_GROUPS` | `readers,analysts` | Database groups the user joins for the session (`GetClusterCredentials` only) |

The AWS identity needs permission to call the API from the table above — `redshift-serverless:GetCredentials` on the workgroup, or `redshift:GetClusterCredentialsWithIAM` / `redshift:GetClusterCredentials` on the `dbname:`/`dbuser:` resources (plus `redshift:JoinGroup` when using `DB_GROUPS`). Credentials are minted per connection and expire, which is why a long-running process may need to reconnect.

## Data types

### Importing

`datacontract import redshift` reads the declared types from the `SVV_COLUMNS` catalog view and writes them as `physicalType` in the catalog's own spelling, including length and precision (`character varying(36)`, `numeric(10,2)`). That is exactly what the physical type check reads back during a test, so an imported contract passes on the first run. The `logicalType` is derived with the same mapping as the SQL import below.

`datacontract import sql --dialect redshift` maps DDL types like the [Postgres dialect](./postgres.md#importing): `VARCHAR`/`CHAR`/`TEXT` → `string`, integer types → `integer`, `NUMERIC`/`DECIMAL`/`REAL`/`DOUBLE PRECISION` → `number`, `BOOLEAN` → `boolean`, `DATE` → `date`, `TIME` → `time`, `TIMESTAMP`/`TIMESTAMP WITH TIME ZONE` → `timestamp`. Redshift-specific types without a portable equivalent (`SUPER`, `GEOMETRY`) get no `logicalType`; the `physicalType` is still written.

### Testing

Redshift supports **native type introspection**: the declared `physicalType` is checked against `information_schema.columns`. `decimal` and `numeric` are interchangeable, as are timezone variants of timestamps; length/precision is only enforced when declared. A `physicalType` that can't be interpreted falls back to the logical type category comparison.

{/* AUTOGENERATED TYPE MAPPING: do not edit by hand; regenerate with update_reference_types.py */}

### Logical type mapping

When no `physicalType` is declared, the CLI derives the native type from the `logicalType` — for example in `datacontract export sql` and the dbt exports. This table is generated from the converter in the CLI's code:

| `logicalType` | Redshift type |
|---|---|
| `string` | `text` |
| `integer` | `integer` |
| `number` | `numeric` |
| `boolean` | `boolean` |
| `date` | `date` |
| `timestamp` | `timestamptz` |
| `time` | `time` |
| `object` | `jsonb` |
| `array` | `text[]` |
| `map` | `jsonb` |

{/* END AUTOGENERATED TYPE MAPPING */}
