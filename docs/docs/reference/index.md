---
sidebar_position: 0
title: "Data Source Reference"
slug: /reference
description: "Authentication options and data type mappings for every data source supported by the Data Contract CLI."
---

# Data Source Reference

Lookup material for every supported data source: all **authentication** options (environment variables) and how **data types** are mapped when importing a contract and checked when testing one. For task-oriented walkthroughs, see [Test your Data](../testing/index.md).

## How authentication works

Connection details (host, catalog, location, …) live in the contract's `servers` block; credentials are provided as environment variables. Variables are also loaded from a `.env` file in the current working directory (or the nearest parent directory containing one); already-set environment variables take precedence.

## How data types work

A contract property carries up to two type declarations:

- **`logicalType`** — one of nine portable ODCS types: `string`, `integer`, `number`, `boolean`, `date`, `timestamp`, `time`, `object`, `array`.
- **`physicalType`** — free text for the native type in the data source (e.g. `VARCHAR(255)`, `NUMBER(38,0)`). It is not validated by `datacontract lint`; at test time it is interpreted in the SQL dialect of the server under test.

When you run `datacontract test`, type checks work in one of two modes:

1. **Native type check** (`Check that field x has physical type y`) — on sources with catalog introspection (Snowflake, BigQuery, Databricks, Postgres, Redshift, SQL Server, Oracle, Trino, Athena), the declared `physicalType` is compared against the actual column type from the catalog. Timezone variants of timestamps are interchangeable; length/precision is only enforced when the contract declares it (`varchar` matches `varchar(255)`, but `varchar(255)` does not match `varchar(100)`). A `physicalType` that can't be interpreted in the server's dialect degrades to the logical check or a warning — never a hard failure.
2. **Logical type check** (`Check that field x has type y`) — everywhere else (and as fallback), both the declared and the actual type are normalized to one of the nine ODCS categories and compared. `integer` and `number` are mutually compatible; a bare `object` or `array` matches any structure with the same base.

For file sources with `format: csv`, `json`, or `avro`, no type checks are generated — the file is read *as* the contract's types, and violations surface as read errors (plus JSON Schema validation for `format: json`).

Independent of the type checks, `logicalTypeOptions` (`minimum`, `maximum`, `minLength`, `maxLength`, `pattern`, `enum`, …) generate value checks that behave identically on every source.

## Data sources

<div className="card-grid">
  <a className="doc-card" href="/reference/athena">
    <img src="/img/icons/athena.svg" alt="" />
    <span><span className="doc-card-title">Amazon Athena</span><span className="doc-card-desc">Authentication and data types</span></span>
  </a>
  <a className="doc-card" href="/reference/redshift">
    <img src="/img/icons/redshift.svg" alt="" />
    <span><span className="doc-card-title">Amazon Redshift</span><span className="doc-card-desc">Authentication and data types</span></span>
  </a>
  <a className="doc-card" href="/reference/s3">
    <img src="/img/icons/s3.svg" alt="" />
    <span><span className="doc-card-title">Amazon S3</span><span className="doc-card-desc">Authentication and data types</span></span>
  </a>
  <a className="doc-card" href="/reference/iceberg">
    <img src="/img/icons/iceberg.svg" alt="" />
    <span><span className="doc-card-title">Apache Iceberg</span><span className="doc-card-desc">Authentication and data types</span></span>
  </a>
  <a className="doc-card" href="/reference/impala">
    <img src="/img/icons/impala.svg" alt="" />
    <span><span className="doc-card-title">Apache Impala</span><span className="doc-card-desc">Authentication and data types</span></span>
  </a>
  <a className="doc-card" href="/reference/azure">
    <img src="/img/icons/azure.svg" alt="" />
    <span><span className="doc-card-title">Azure Blob / ADLS</span><span className="doc-card-desc">Authentication and data types</span></span>
  </a>
  <a className="doc-card" href="/reference/databricks">
    <img src="/img/icons/databricks.svg" alt="" />
    <span><span className="doc-card-title">Databricks</span><span className="doc-card-desc">Authentication and data types</span></span>
  </a>
  <a className="doc-card" href="/reference/bigquery">
    <img src="/img/icons/bigquery.svg" alt="" />
    <span><span className="doc-card-title">Google BigQuery</span><span className="doc-card-desc">Authentication and data types</span></span>
  </a>
  <a className="doc-card" href="/reference/gcs">
    <img src="/img/icons/gcs.svg" alt="" />
    <span><span className="doc-card-title">Google Cloud Storage</span><span className="doc-card-desc">Authentication and data types</span></span>
  </a>
  <a className="doc-card" href="/reference/api">
    <img src="/img/icons/api.svg" alt="" />
    <span><span className="doc-card-title">HTTP API</span><span className="doc-card-desc">Authentication and data types</span></span>
  </a>
  <a className="doc-card" href="/reference/kafka">
    <img src="/img/icons/kafka.svg" alt="" />
    <span><span className="doc-card-title">Kafka</span><span className="doc-card-desc">Authentication and data types</span></span>
  </a>
  <a className="doc-card" href="/reference/local">
    <img src="/img/icons/local.svg" alt="" />
    <span><span className="doc-card-title">Local files</span><span className="doc-card-desc">Data types for CSV, JSON, Parquet, Delta</span></span>
  </a>
  <a className="doc-card" href="/reference/sqlserver">
    <img src="/img/icons/sqlserver.svg" alt="" />
    <span><span className="doc-card-title">Microsoft SQL Server</span><span className="doc-card-desc">Authentication and data types</span></span>
  </a>
  <a className="doc-card" href="/reference/mysql">
    <img src="/img/icons/mysql.svg" alt="" />
    <span><span className="doc-card-title">MySQL</span><span className="doc-card-desc">Authentication and data types</span></span>
  </a>
  <a className="doc-card" href="/reference/oracle">
    <img src="/img/icons/oracle.svg" alt="" />
    <span><span className="doc-card-title">Oracle</span><span className="doc-card-desc">Authentication and data types</span></span>
  </a>
  <a className="doc-card" href="/reference/postgres">
    <img src="/img/icons/postgres.svg" alt="" />
    <span><span className="doc-card-title">Postgres</span><span className="doc-card-desc">Authentication and data types</span></span>
  </a>
  <a className="doc-card" href="/reference/snowflake">
    <img src="/img/icons/snowflake.svg" alt="" />
    <span><span className="doc-card-title">Snowflake</span><span className="doc-card-desc">Authentication and data types</span></span>
  </a>
  <a className="doc-card" href="/reference/dataframe">
    <img src="/img/icons/spark.svg" alt="" />
    <span><span className="doc-card-title">Spark DataFrame</span><span className="doc-card-desc">Data types for in-memory DataFrames</span></span>
  </a>
  <a className="doc-card" href="/reference/trino">
    <img src="/img/icons/trino.svg" alt="" />
    <span><span className="doc-card-title">Trino</span><span className="doc-card-desc">Authentication and data types</span></span>
  </a>
</div>
