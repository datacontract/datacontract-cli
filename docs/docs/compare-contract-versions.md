---
sidebar_position: 8
title: "Compare contract versions"
description: "Describe differences and classify backward-compatibility impact between two ODCS data contracts."
---

# Compare contract versions

Use `datacontract changelog` to describe the differences between two versions of a contract, or use `datacontract breaking` to classify their backward-compatibility impact.

## Changelog

Use `datacontract changelog` to compare the source contract (`v1`) with the target contract (`v2`) and report the changes between them:

```bash
datacontract changelog v1.odcs.yaml v2.odcs.yaml
```

See the generated [changelog command reference](./commands/changelog.md) for all options.

## Breaking changes

Use `datacontract breaking` when a contract change must be checked for backward compatibility. The command compares the source contract (`v1`) with the target contract (`v2`) and preserves the detailed changelog while adding a severity classification.

```bash
datacontract breaking v1.odcs.yaml v2.odcs.yaml
```

See the generated [breaking command reference](./commands/breaking.md) for all options.

### Severity levels

- **ERROR** - a backward-incompatible change. The command exits with status `1`.
- **WARNING** - a potentially incompatible change that requires review. The command exits with status `0`.
- **INFO** - informational or currently unclassified metadata. The command exits with status `0`.

The result is breaking only when at least one detailed entry has severity `ERROR`.

### Initial compatibility rules

The first ODCS implementation treats schema and property removals, requiredness tightening, type changes, and uniqueness tightening as errors. Primary-key changes and changes to validation constraints whose direction cannot be proven are warnings. Additions, relaxed constraints, descriptions, tags, business names, custom properties, and unrecognized changes are informational unless a more specific rule applies.

Every detailed changelog entry receives exactly one classification. Unknown fields use the informational fallback so that introducing a new ODCS field does not make detection fail.

### API

The same result is available from `POST /breaking`, using the same JSON request shape as `POST /changelog`:

```json
{
  "v1": "<source contract YAML>",
  "v2": "<target contract YAML>"
}
```

The response includes `summary`, `entries`, and an `is_breaking` boolean. The endpoint returns HTTP `200` for a valid comparison even when `is_breaking` is `true`; invalid YAML or contracts return HTTP `422`.