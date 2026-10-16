---
sidebar_position: 8
title: "Compare contract versions"
description: "Describe differences and classify compatibility impact between two ODCS data contracts."
---

# Compare contract versions

Use `datacontract changelog` to describe the differences between two versions of a contract, or use `datacontract breaking` to classify their compatibility impact.

## Changelog

Use `datacontract changelog` to compare the source contract (`v1`) with the target contract (`v2`) and report the changes between them:

```bash
datacontract changelog v1.odcs.yaml v2.odcs.yaml
```

See the generated [changelog command reference](./commands/changelog.md) for all options.

## Breaking changes

Use `datacontract breaking` when a contract change must be checked for compatibility. The command compares the source contract (`v1`) with the target contract (`v2`) and preserves the detailed changelog while adding a severity classification.

```bash
datacontract breaking v1.odcs.yaml v2.odcs.yaml
```

See the generated [breaking command reference](./commands/breaking.md) for all options.

### Perspectives

Whether a change breaks depends on whose expectations it must keep. `--perspective` selects one of two:

- **`consumer`** (default) - "If we change the data in this way, will the expectations of data users break?"
- **`producer`** - "If we change the contract in this way, will the next contract test fail?"

```bash
datacontract breaking --perspective producer v1.odcs.yaml v2.odcs.yaml
```

### Severity levels

- **ERROR** - a breaking change from the selected perspective. The command exits with status `1`.
- **WARNING** - a change that may break and requires review. The command exits with status `0`.
- **INFO** - a change that does not break from the selected perspective. The command exits with status `0`.

The result is breaking only when at least one detailed entry has severity `ERROR`.

### API

The same result is available from `POST /breaking`, using the same JSON request shape as `POST /changelog` and an optional `perspective` query parameter:

```json
{
  "v1": "<source contract YAML>",
  "v2": "<target contract YAML>"
}
```

The response includes `summary`, `entries`, the `perspective` it was graded from, and an `is_breaking` boolean. The endpoint returns HTTP `200` for a valid comparison even when `is_breaking` is `true`; invalid YAML or contracts return HTTP `422`.