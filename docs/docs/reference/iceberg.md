---
sidebar_position: 4
title: "Apache Iceberg Reference"
sidebar_label: "Apache Iceberg"
description: "Authentication and data type handling for Apache Iceberg REST catalogs."
---

# <img className="page-icon" src="/img/icons/iceberg.svg" alt="" /> Apache Iceberg Reference

Authentication and data type handling for [Apache Iceberg connections](../testing/iceberg.md).

## Server

```yaml
servers:
  - server: production
    type: iceberg
    catalog: main                                       # the catalog's name
    catalogUrl: https://polaris.example.com/api/catalog # the REST catalog endpoint
    namespace: sales                                    # optional; prefixed to every table name
    warehouse: s3://warehouse                           # optional; passed to the catalog
```

## Configuration

| Environment variable | Purpose |
|---|---|
| `DATACONTRACT_ICEBERG_CREDENTIAL` | OAuth2 client credential for the catalog, as `client_id:client_secret` |
| `DATACONTRACT_ICEBERG_TOKEN` | Bearer token for the catalog, instead of a credential |
| `DATACONTRACT_ICEBERG_CATALOG_URL`, `DATACONTRACT_ICEBERG_CATALOG`, `DATACONTRACT_ICEBERG_NAMESPACE`, `DATACONTRACT_ICEBERG_WAREHOUSE` | Override the matching field of the contract's `servers` block |
| `DATACONTRACT_ICEBERG_CATALOG_TYPE` | The pyiceberg catalog implementation: `rest` (default), `sql`, `glue`, `hive`, `dynamodb`. For `sql`, `catalogUrl` is the SQLAlchemy connection URI |
| `DATACONTRACT_S3_ACCESS_KEY_ID`, `DATACONTRACT_S3_SECRET_ACCESS_KEY`, `DATACONTRACT_S3_SESSION_TOKEN`, `DATACONTRACT_S3_REGION` | Credentials for the data files on S3; not needed when the catalog vends them |
| `DATACONTRACT_ICEBERG_S3_ENDPOINT` | Endpoint of an S3-compatible store (MinIO, Ceph) holding the data files |

The full list is on the [Configuration](../configuration.md) page.

## Data types

### Importing

`datacontract import iceberg` reads the table schema from the catalog (or from a schema JSON file with `--source`):

| Iceberg type | `logicalType` |
|---|---|
| `string`, `uuid` | `string` |
| `int`, `long` | `integer` |
| `float`, `double`, `decimal(p,s)` | `number` |
| `boolean` | `boolean` |
| `date` | `date` |
| `timestamp`, `timestamptz` | `timestamp` |
| `time` | `time` |
| `struct<...>` | `object` with `properties` |
| `list<...>` | `array` with `items` |
| `map<k,v>` | `map` with `key` and `value` |
| `binary`, `fixed` | `string` |

The Iceberg type is kept as `physicalType`, and the field id as the `icebergFieldId` custom property.

### Testing

The table is scanned to Arrow and registered in DuckDB, so the type checks compare the declared `logicalType` against the DuckDB type of the Arrow column: structs become `STRUCT`, lists `LIST`, and maps `MAP`, which the nested type checks walk. `physicalType` checks against the catalog's declared type are not run for Iceberg; the logical type check runs instead.

### Exporting

`datacontract export iceberg` writes an Iceberg schema JSON from the contract; the mapping is the reverse of the import table above, with `number` becoming `decimal(38,0)` and `integer` becoming `long`.
