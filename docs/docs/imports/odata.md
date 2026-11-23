---
sidebar_position: 21
title: "Import: OData"
description: "Create a data contract from OData 4.x entity sets and singletons using CSDL XML or JSON."
---

# <img className="page-icon" src="/img/icons/odata.svg" alt="" /> Import: OData

Creates a data contract from OData 4.x CSDL XML or JSON metadata. Select individual entity sets and singletons, or automatically import all of them advertised in the service document. Both public and authenticated services are supported.

```bash
datacontract import odata \
  --service-root-url 'https://xmart-api-public-uat.who.int/refmart/' \
  --resource ref_country \
  --output datacontract.yaml
```

This example imports the WHO [country endpoint](https://xmart-api-public-uat.who.int/refmart/ref_country). `--service-root-url` is always required and is stored with a trailing `/` as the server's `location`. Metadata is read from `$metadata` under that root unless you supply `--metadata-url` or `--metadata-file`.

Repeat `--resource` to select multiple entity sets and singletons.

An explicit selection skips the service document. Without a selection, the importer reads the JSON service document from the root URL and imports every entity set and singleton listed there into the same contract. Functions and linked services are skipped.

`--entity-set` remains available as a hidden compatibility alias for `--resource`.

For offline import, supply a local CSDL XML or JSON file through `--metadata-file`. Also supply `--service-document-file` or select resources with `--resource`.

For authentication, set `DATACONTRACT_API_HEADER_AUTHORIZATION` to the complete header value, such as `Bearer <token>` or a precomputed `Basic <base64-encoded username:password>`. Set `DATACONTRACT_API_HEADER_X_API_KEY` for services that require an `X-API-Key` header.

The importer reads metadata only; no data records are fetched. It preserves field types, nullability, declared keys and constraints. Types without a logical type mapping, including complex types, collection-valued fields, enums and type definitions, are imported with their `physicalType` but without `logicalType` and produce a warning. Collections use `Collection(...)` as their `physicalType`. Inheritance causes errors when used by a selected schema. External metadata references are not downloaded.

Navigation properties with referential constraints produce `foreignKey` relationships. Single-property constraints are stored on the referencing property; composite constraints are stored as one schema-level relationship with matching `from` and `to` arrays. Navigation bindings identify the target entity set or singleton, which must also be selected.

OData support currently covers import only. Support for `datacontract test` is planned to compare the contract's schema with `$metadata`, without fetching data records.

All options: **[`datacontract import odata`](../commands/import/odata.md)**.
