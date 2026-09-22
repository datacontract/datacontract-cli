---
sidebar_position: 18
title: "Import: OData"
description: "Create a data contract from one or more OData 4.x EntitySets using CSDL XML or JSON."
---

# <img className="page-icon" src="/img/icons/api.svg" alt="" /> Import: OData

Import one or more EntitySets from **OData 4.x** into an ODCS 3.2.0 contract.

- **Select specific EntitySets:** Use `--entity-set Products` for one EntitySet, or repeat the option to select several.
- **Import all automatically:** Omit `--entity-set` to import every EntitySet listed in the service document into one contract.

CSDL XML or JSON provides field types and constraints. The service document can be fetched from the service root
or read from a local file with `--service-root-file`. No data records are downloaded.

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `--service-root-url` | Yes | HTTP(S) root URL of the OData service. Stored with exactly one trailing `/` as the server's `location`, including for offline imports. |
| `--service-root-file` | No | Path to a local JSON service document listing the available EntitySets. Without this option, the service document is fetched from the root URL. Ignored when `--entity-set` is supplied. |
| `--entity-set` | No | Name of an EntitySet to import. Repeat to select several. If omitted, import all EntitySets listed in the service document. Explicit selection skips reading the service document. |
| `--metadata-url` | No | HTTP(S) URL of the CSDL XML or JSON metadata. Defaults to `SERVICE_ROOT_URL/$metadata` when neither metadata option is supplied. |
| `--metadata-file` | No | Path to a local OData CSDL XML or JSON metadata file. |
| `--output` | No | Path to the generated data contract YAML file. If omitted, print the contract to stdout. |
| `--owner` | No | Owner or team name to assign to the generated contract. |
| `--id` | No | Identifier to assign to the generated contract. |
| `--debug` / `--no-debug` | No | Control debug logging; use `--debug` for diagnostic output. |
| `--help` | No | Show the command's options and exit. |

`--metadata-url` and `--metadata-file` cannot be combined. For an import without network access, use
`--metadata-file` together with either `--entity-set` or `--service-root-file`.

## Example: WHO countries

The WHO [country endpoint](https://xmart-api-public-uat.who.int/refmart/ref_country) is described by its
[metadata document](https://xmart-api-public-uat.who.int/refmart/$metadata).

```bash
datacontract import odata \
  --service-root-url 'https://xmart-api-public-uat.who.int/refmart/' \
  --entity-set ref_country \
  --output datacontract.yaml
```

`--service-root-url` is required and is stored with exactly one trailing `/` as the server's `location`.
A trailing slash is optional in the input.

If neither `--metadata-file` nor `--metadata-url` is supplied, metadata is fetched from the service root
with `$metadata` appended. Use `--metadata-url` to override that address; quote URLs containing `$metadata`
with single quotes to prevent shell expansion. The two metadata options are mutually exclusive.

The importer matches EntitySet names exactly first. If there is no exact match, it accepts a case-insensitive
match only when unique. Ambiguous or missing matches produce an error. For WHO, `ref_country` matches
`REF_COUNTRY`; the schema keeps the metadata name.

Omit `--output` to print YAML to stdout. Use `--owner` and `--id` to override the contract's owner and identifier.

## Multiple EntitySets

Repeat `--entity-set` to select several EntitySets:

```bash
datacontract import odata \
  --service-root-url 'https://example.com/odata/' \
  --entity-set Products \
  --entity-set Orders \
  --output datacontract.yaml
```

Explicit selection reads only CSDL. It does not request the service root or read `--service-root-file`,
even if that option is supplied. Argument order is preserved; repeated selections of the same EntitySet
produce one schema object. EntitySets sharing an EntityType still produce separate schema objects.

Without `--entity-set`, the importer reads the JSON service document from `--service-root-file`, if supplied,
or from `--service-root-url`. It imports the EntitySets advertised there, in document order. It does not
fall back to importing all EntitySets from CSDL. Singletons, function imports and linked services are ignored.
An omitted `kind` in a service document entry means `EntitySet`.

One EntitySet gives the contract its name. For multiple EntitySets, the contract uses the service container's name.
Missing or ambiguous EntitySets, duplicate entries in the service document and empty selections produce errors.
If any selected schema uses unsupported types, the whole import fails before writing the output file.

## Offline import

Use a local CSDL file and an explicit selection to import without any network requests:

```bash
datacontract import odata \
  --service-root-url 'https://example.com/odata/' \
  --metadata-file metadata.xml \
  --entity-set Products \
  --entity-set Orders \
  --output datacontract.yaml
```

Alternatively, provide both documents locally to import every advertised EntitySet:

```bash
datacontract import odata \
  --service-root-url 'https://example.com/odata/' \
  --service-root-file service-document.json \
  --metadata-file metadata.json \
  --output datacontract.yaml
```

CSDL XML and JSON are detected from content, regardless of file extension or HTTP `Content-Type`.
Both formats also work with `--metadata-url`. Relative file paths are resolved from the current working directory.
Metadata saved from an authenticated service can be imported offline.

`--service-root-file` alone does not guarantee offline import: CSDL must also be supplied through
`--metadata-file`. Conversely, `--metadata-file` without an explicit selection or a local service document
still causes a request to the service root.

## Generated contract

The server describes the service, and each schema object identifies its own EntitySet:

```yaml
servers:
  - server: source
    type: api
    location: https://example.com/odata/
    customProperties:
      - property: apiType
        value: odata
      - property: odataVersion
        value: "4.01"
      - property: odataMetadataUrl
        value: https://example.com/odata/$metadata
      - property: format
        value: json
schema:
  - name: Products
    physicalName: Products
    logicalType: object
    physicalType: object
    customProperties:
      - property: odataEntitySet
        value: Products
      - property: odataEntitySetUrl
        value: https://example.com/odata/Products
    # properties: ...
```

These custom properties are Data Contract CLI conventions for future OData-aware consumers.
`odataVersion` records the CSDL response version, or the document version for file imports.
`odataMetadataFile` replaces `odataMetadataUrl` for local CSDL files.
`format: json` describes the data response, independently of the metadata format; ODCS API servers do not
permit a top-level `format` field.

`odataEntitySet` now belongs to each schema object, including for single-EntitySet imports.
`odataEntitySetUrl` records the advertised address when reading a service document. Relative addresses are
resolved using OData's context URL rules, with the service root as the document base for local files.
With explicit selection, the URL is constructed from the service root and the EntitySet name in CSDL.
Context links and EntitySet addresses are never fetched, and context links do not override the metadata source.

## Supported schema

| OData type | ODCS logical type |
|---|---|
| `Edm.String`, `Edm.Guid` | `string` (`uuid` format for Guid) |
| `Edm.Byte`, `Edm.SByte`, `Edm.Int16`, `Edm.Int32`, `Edm.Int64` | `integer` |
| `Edm.Decimal`, `Edm.Single`, `Edm.Double` | `number` |
| `Edm.Boolean` | `boolean` |
| `Edm.Date` | `date` |
| `Edm.DateTimeOffset` | `timestamp` |
| `Edm.TimeOfDay` | `time` |

Original types are preserved in `physicalType`. The importer copies nullability, declared primary keys and their
positions, numeric maximum lengths, precision and scale. Precision and scale use property-level custom properties;
symbolic scale values are preserved. No primary keys are inferred when metadata omits them, as in the WHO example.

Qualified type names and local schema aliases work across schemas. JSON selects the service container with
`$EntityContainer`; XML must identify one unambiguous, named EntityContainer.
Omitted `Nullable` means nullable in XML; omitted `$Nullable` means required in JSON.
In JSON, omitted `$Type` means `Edm.String`, and a decimal's omitted `$Scale` means `variable`.
An omitted `$Precision` introduces no precision constraint.

## Current limitations

- The service root must not contain credentials, query parameters or a fragment.
- Service documents must be JSON; CSDL supports both XML and JSON.
- All version strings of the form `4.x` are accepted, with no upper minor-version limit.
  Requests do not send `OData-MaxVersion`. Other major versions, malformed versions and conflicting
  CSDL document/header versions are rejected. Later 4.x versions use the same supported schema constructs;
  accepting their version numbers does not add support for new OData features.
- Complex types, collection-valued fields, entity or container inheritance, enum types, type definitions and
  types outside the table produce errors when used by selected schemas.
- Navigation properties are omitted with a warning. External metadata references are not downloaded.
- Malformed documents, duplicate JSON keys and XML DTD declarations are rejected.
- This feature implements **import only**.

## Planned improvements

- **`datacontract test`:** Validate the contract's schema against the service's `$metadata` document.
  Testing will only read metadata and will not fetch EntitySets or data records.

This capability is planned and is not yet implemented.

## Authentication

For authenticated services, set `DATACONTRACT_API_HEADER_AUTHORIZATION` to the complete `Authorization`
header value. For example, use a Bearer token supplied by your service:

```bash
export DATACONTRACT_API_HEADER_AUTHORIZATION="Bearer ${ODATA_ACCESS_TOKEN}"
datacontract import odata \
  --service-root-url 'https://example.com/odata/' \
  --output datacontract.yaml
```

A precomputed `Basic <base64-encoded username:password>` header works too. The importer does not obtain
or refresh tokens. Without this setting, requests are anonymous; `.netrc` credentials are not used.

The same header is sent to both the metadata URL and the service root when those documents are fetched,
including an explicitly supplied `--metadata-url` on another host. Requests' redirect rules remove the
header when redirecting to another host or downgrading from HTTPS to HTTP. Once removed, it is not
restored later in that redirect chain. Credentials are not written to the generated contract.

You can also use the existing global `--config-file` option:

```yaml
# datacontract-config.yaml
api_header_authorization: "Bearer ${ODATA_ACCESS_TOKEN}"
```

```bash
datacontract --config-file datacontract-config.yaml import odata \
  --service-root-url 'https://example.com/odata/' \
  --output datacontract.yaml
```

Explicit configuration takes precedence over the environment. Fully offline imports do not use the header
or make network requests. See [Configuration](../configuration.md) for all supported configuration sources.

## Python

```python
from datacontract.data_contract import DataContract

contract = DataContract.import_from_source(
    "odata",
    source="https://example.com/odata/",
    odata_metadata_file="metadata.json",
    odata_entity_set=["Products", "Orders"],
)
print(contract.to_yaml())
```

`source` is now the service root URL. Use `odata_metadata_url` for an explicit metadata URL,
or omit both metadata arguments to derive the URL from `source`. For offline import of all advertised sets,
replace `odata_entity_set` with `odata_service_root_file="service-document.json"`.
File arguments accept strings or `Path` objects; `odata_entity_set` accepts a non-empty list of names.

For an authenticated URL import, pass the existing `Config` option:

```python
import os

from datacontract import Config
from datacontract.data_contract import DataContract

contract = DataContract.import_from_source(
    "odata",
    source="https://example.com/odata/",
    odata_entity_set=["Products"],
    config=Config(api_header_authorization=f"Bearer {os.environ['ODATA_ACCESS_TOKEN']}"),
)
```

The `config` argument also accepts a dictionary keyed by `DATACONTRACT_API_HEADER_AUTHORIZATION`.

All options: **[`datacontract import odata`](../commands/import/odata.md)**.
