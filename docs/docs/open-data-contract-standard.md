---
sidebar_position: 3
title: "Open Data Contract Standard"
description: "The Data Contract CLI natively uses the Open Data Contract Standard (ODCS) as its contract format."
---

# Open Data Contract Standard

The Data Contract CLI natively uses the **[Open Data Contract Standard (ODCS)](https://bitol-io.github.io/open-data-contract-standard/latest/)** as its data contract format. ODCS is an open, vendor-neutral standard maintained by the [Bitol](https://bitol.io/) project under the Linux Foundation's AI & Data umbrella.

A data contract written in ODCS is a single YAML file that describes a data set's structure, semantics, quality, ownership, and the servers where the data lives.

## A minimal contract

```yaml
apiVersion: v3.0.2
kind: DataContract
id: urn:datacontract:checkout:orders-latest
name: orders
version: 1.0.0
status: active
description:
  purpose: One record per order. Includes cancelled and deleted orders.
servers:
  - server: production
    type: postgres
    host: localhost
    port: 5432
    database: orders
    schema: public
schema:
  - name: orders
    physicalName: orders
    properties:
      - name: order_id
        logicalType: string
        physicalType: uuid
        primaryKey: true
        required: true
      - name: order_total
        logicalType: integer
        physicalType: integer
        required: true
        quality:
          - type: sql
            description: 95% of order totals are between 10 and 499 EUR
            query: SELECT quantile_cont(order_total, 0.95) FROM orders
            mustBeBetween: [1000, 99900]
```

:::note
The CLI also accepts the older Data Contract Specification format (which uses `models`/`fields` instead of ODCS `schema`/`properties`), but new contracts should follow ODCS — all examples in this documentation use ODCS. Use [`datacontract init`](./commands/init.md) to start from a current template.
:::

## Key sections

| Section | Purpose |
|---|---|
| `apiVersion` / `kind` | Identifies the document as an ODCS data contract and its version. |
| `id`, `name`, `version`, `status` | Identity and lifecycle of the contract. |
| `description` | Human-readable purpose, usage, and limitations. |
| `servers` | Where the data physically lives — the connection details used by [`test`](./commands/test.md). One contract can have several servers. |
| `schema` | The logical structure: schemas (tables/objects) and their properties (columns/fields), types, constraints, and semantics. |
| `quality` | Data quality rules, attached to the schema or to individual properties. See [Quality Rules](./quality-rules.md). |
| `slaProperties` | Service-level expectations such as freshness, retention, and frequency. |
| `team` / `roles` | Ownership and access information. |
| `customProperties` | Extension point for backend-specific settings (for example `clickhouseType`, `trinoType`, `avroLogicalType`). |

## Logical vs. physical types

ODCS separates the **logical type** (`logicalType`, e.g. `string`, `integer`, `number`, `boolean`, `date`, `timestamp`) from the **physical type** (`physicalType`, e.g. `varchar`, `uuid`, `INT64`).

- The CLI uses the logical type as the portable, server-independent description.
- When you select a server (via `--server` or the server `type`), the CLI maps logical types to that backend's physical types for [exports](./exports/index.md) and [tests](./testing.md).
- You can always override the physical type per field, or pin a backend-specific type via `customProperties` / `config` (for example `clickhouseType`, `trinoType`).

## Working with ODCS in the CLI

- **Author** contracts with [`datacontract init`](./commands/init.md) and the [Data Contract Editor](./editor.md).
- **Validate** the structure against the ODCS JSON Schema with [`datacontract lint`](./commands/lint.md). Pass `--json-schema` to use a specific schema version.
- **Compare** two versions of a contract with [`datacontract changelog`](./commands/changelog.md).
- **Generate** a contract from an existing system using the [importers](./imports/index.md).

## Learn more

- ODCS specification: [bitol-io.github.io/open-data-contract-standard](https://bitol-io.github.io/open-data-contract-standard/latest/)
- Data contracts overview: [datacontract.com](https://datacontract.com)
