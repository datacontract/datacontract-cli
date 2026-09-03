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

Only `type: semantics` (and the older `semantic` and `definition`) links are resolved. The `glossary`, `ontology` and `taxonomy` types that ODCS v3.2.0 recommends are kept as links: the HTML export shows them, and nothing is merged from them.

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

When a property carries several links, the highest-precedence one wins and is the only one fetched: **`semantics`** → `semantic` (the legacy singular spelling, still accepted) → `definition`.

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
