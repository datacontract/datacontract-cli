---
sidebar_position: 18
title: "Import: OData"
description: "Create a data contract from one or more OData 4.x EntitySets using CSDL XML or JSON."
---

# <img className="page-icon" src="/img/icons/api.svg" alt="" /> Import: OData

Creates a data contract from OData 4.x CSDL XML or JSON metadata. Select individual EntitySets, or automatically import all EntitySets advertised in the service document. Both public and authenticated services are supported.

```bash
datacontract import odata \
  --service-root-url 'https://xmart-api-public-uat.who.int/refmart/' \
  --entity-set ref_country \
  --output datacontract.yaml
```

This example imports the WHO [country endpoint](https://xmart-api-public-uat.who.int/refmart/ref_country). `--service-root-url` is always required and is stored with a trailing `/` as the server's `location`. Metadata is read from `$metadata` under that root unless you supply `--metadata-url` or `--metadata-file`.

Repeat `--entity-set` to select several EntitySets. An explicit selection skips the service document. Without `--entity-set`, the importer reads the JSON service document from the root URL and imports every EntitySet listed there into the same contract.

For offline import, supply a local CSDL XML or JSON file through `--metadata-file`. Also supply `--service-root-file` or `--entity-set`.

For authentication, set `DATACONTRACT_API_HEADER_AUTHORIZATION` to the complete header value, such as `Bearer <token>` or a precomputed `Basic <base64-encoded username:password>`.

The importer reads metadata only; no data records are fetched. It preserves supported primitive field types, nullability, declared keys and constraints. Complex types, collection-valued fields, enums, type definitions, inheritance and unsupported primitive types cause errors when used by a selected schema. Navigation properties are omitted, and external metadata references are not downloaded.

OData support currently covers import only. Support for `datacontract test` is planned to compare the contract's schema with `$metadata`, without fetching data records.

All options: **[`datacontract import odata`](../commands/import/odata.md)**.
