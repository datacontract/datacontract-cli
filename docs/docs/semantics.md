---
sidebar_position: 10
title: "Link your Semantics"
description: "Link a property to a shared semantic concept or reusable definition with ODCS authoritativeDefinitions, by URL or IRI, and let the CLI inline it."
---

# Link your Semantics

A property does not have to carry its full meaning inline. With the ODCS `authoritativeDefinitions` attribute, a property can **link to a shared semantic concept** — a business term defined once, centrally — and the CLI resolves that link and inlines the definition before linting, testing, or exporting the contract.

```yaml
schema:
  - name: orders
    properties:
      - name: article
        authoritativeDefinitions:
          - type: semantics
            url: http://www.entropy-data.com/ns/main/Article
```

The referenced concept supplies the description, business name, logical type, and anything else it defines, so every contract that links to it stays consistent by construction.

## URL or IRI

The `url` of a `type: semantics` link may be either of the two shapes ODCS allows, and the CLI resolves each differently:

| `url` | Resolved as |
|---|---|
| A path or an absolute URL on the configured host — `/demo/semantics/main/product.brand` | **REST URL** — fetched directly |
| An absolute URL on any other host — `http://www.entropy-data.com/ns/main/Article` | **IRI** — an identifier, not an address; looked up through `/api/semantics?iri=…` on the configured host |

An IRI names a concept but is usually not fetchable at its own address, so the CLI never dereferences it directly. It URL-encodes the IRI and asks the configured host to resolve it.

## Reusable definitions

`type: definition` links to a reusable ODCS property definition instead of a semantic concept:

```yaml
properties:
  - name: customer_email
    authoritativeDefinitions:
      - type: definition
        url: https://example.com/definitions/email.json
```

A `definition` URL on a different host is fetched **directly and anonymously** — a contract may legitimately point at a third-party URL, and the API key is never sent across hosts.

When a property carries several links, the highest-precedence one wins and is the only one fetched: **`semantics`** → `semantic` (the legacy singular spelling, still accepted) → `definition` → `businessDefinition`.

## Reference a file

A link may also point at a file next to the contract instead of a server. This is the shape to reach for when the business meaning of a field is described in the same repository, and no server is involved. There are two ways to write it, depending on where the definition lives.

### A property in another contract

Use a `<file>#<fragment>` reference when the meaning belongs to a property of another contract — typically a business-level contract that a technical contract materializes:

```yaml
# top-artists-by-year-view.odcs.yaml
properties:
  - name: artist_name
    logicalType: string
    physicalType: character
    authoritativeDefinitions:
      - type: businessDefinition
        url: top-artists-by-year.odcs.yaml#schema/top_artists_by_year_ba/properties/artist_name
```

The technical contract keeps `logicalType`, `physicalType`, and `primaryKey`, and inherits `businessName`, `description`, `examples`, and everything else the business attribute defines. See [`examples/business-definitions`](https://github.com/datacontract/datacontract-cli/tree/main/examples/business-definitions) for the full pair.

**The fragment** walks the referenced contract:

```
#schema/<schema>/properties/<property>[/properties/<nested>]…[/items]
```

Each step matches on `id` first and falls back to `name`. Contracts that carry stable ids should reference by `id` — that keeps the link intact when a human-readable `name` changes. The fragment has to end at a property; it cannot point at a schema object.

### A file that is the definition

Leave the fragment off, and the file *is* the definition: it holds the elements of the property directly, with no contract around them. This is the shape for a glossary kept as one file per term:

```yaml
# definitions/shipment_id.odcs.yaml
businessName: Shipment ID
description: Unique identifier for each shipment.
logicalType: string
examples:
  - 123e4567-e89b-12d3-a456-426614174000
```

```yaml
# shipments.odcs.yaml
properties:
  - name: sid
    physicalType: uuid
    authoritativeDefinitions:
      - type: businessDefinition
        url: definitions/shipment_id.odcs.yaml
```

A fragment-less url is read from disk when it names a `.yaml`, `.yml`, or `.json` file. Everything else without a fragment stays what it has always been — a path on the configured host, e.g. `url: /definitions/shipment_id`.

### Both shapes

**The file path** is relative to the contract that holds the reference, so a checked-out directory resolves from any working directory. Absolute paths work too. A contract read from an HTTP URL cannot resolve a file reference.

The type of the link says what the reference *means*; the shape of the `url` says where it *lives*. Every resolvable type — `semantics`, `semantic`, `definition`, `businessDefinition` — accepts a file reference and a URL alike, so the two are never tied together.

Chains resolve: if the referenced business attribute itself links to a glossary file or a semantic concept, that link is resolved before the value is inlined. A cycle between files is reported as an error rather than followed.

## How the definition is merged

The resolved definition fills in only what the property leaves unset — **inline values always win**:

```yaml
properties:
  - name: article
    description: The article as sold in the German shop   # kept
    authoritativeDefinitions:                             # supplies logicalType,
      - type: semantics                                   # businessName, tags, …
        url: http://www.entropy-data.com/ns/main/Article
```

These are never merged, because they belong to the contract author: `id`, `name`, `authoritativeDefinitions` itself, and the `properties` / `items` that make up the structure.

This is the same for a link to a semantic concept, a reusable definition, and a business attribute in another file.

Resolution recurses into nested `properties` and array `items`, so a link on a deeply nested field resolves too. Successful lookups are cached per run; failures are not, so a transient error retries on the next run.

## Configuration

| Environment variable | Purpose |
|---|---|
| `ENTROPY_DATA_HOST` | The host that resolves references. Defaults to `https://api.entropy-data.com`. Falls back to the deprecated `DATAMESH_MANAGER_HOST`, then `DATACONTRACT_MANAGER_HOST`. |
| `ENTROPY_DATA_API_KEY` | Sent as `x-api-key`, and **only** to the configured host. Falls back to the deprecated `DATAMESH_MANAGER_API_KEY`, then `DATACONTRACT_MANAGER_API_KEY`. |

An IRI lookup always requires an API key — `/api/semantics` is API-key only. A REST URL on the configured host uses the key when one is set.

## Turning resolution off

Resolution runs by default on [`lint`](./commands/lint.md), [`test`](./commands/test.md), [`ci`](./commands/ci.md), [`changelog`](./commands/changelog.md), and every [`export`](./commands/export/index.md) format. Pass `--no-inline-references` to skip it and work with the contract exactly as written:

```bash
datacontract lint --no-inline-references datacontract.yaml
```

:::caution
A reference that cannot be resolved **rejects the contract** — the command fails rather than silently continuing with an incomplete property. If the error is a 401 or 403, the configured host is usually the wrong deployment for that IRI; the message includes the `ENTROPY_DATA_HOST` to set.
:::

## Learn more

- The `authoritativeDefinitions` syntax is part of the [Open Data Contract Standard](https://bitol-io.github.io/open-data-contract-standard/latest/).
- Semantic concepts are managed in [Entropy Data](./entropy-data.md).
