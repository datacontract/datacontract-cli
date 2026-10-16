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

- **`consumer`** (default) - a change is breaking when v2 permits data that v1 ruled out, so a guarantee consumers relied on no longer holds. Removing a property and loosening a constraint break; adding a property and tightening a constraint do not.
- **`producer`** - a change is breaking when v2 rules out data that v1 permitted, so data that passed [`datacontract test`](./commands/test.md) against v1 may fail against v2. Adding a property and tightening a constraint break; removing a property and loosening a constraint do not.

```bash
datacontract breaking --perspective producer v1.odcs.yaml v2.odcs.yaml
```

### Directions

Every change has a direction, independent of the perspective, which the perspective turns into a severity:

| Direction | Meaning | `consumer` | `producer` |
|---|---|---|---|
| `tightens` | v2 rules out more data | INFO | ERROR |
| `loosens` | v2 permits more data | ERROR | INFO |
| `both` | v2 rules out some data v1 permitted and permits some v1 ruled out | ERROR | ERROR |
| `undetermined` | depends on content the CLI cannot compare | WARNING | WARNING |
| `untested` | changes nothing `datacontract test` checks | INFO | INFO |

- **Tightens** - adding a schema or property, a type where there was none, `required`, `unique`, `uniqueItems`, a primary key, an enum, a foreign key relationship, a blocking quality rule, or a `freshness` service level; raising a minimum or lowering a maximum (`minLength`, `maxLength`, `minimum`, `maximum`, `minItems`, `maxItems`, quality thresholds); narrowing `mustBeBetween` or widening `mustNotBeBetween`; removing an enum value or a `validValues` value; adding an `invalidValues` value; shortening a `freshness` duration; making a quality rule blocking.
- **Loosens** - the reverse of each of these.
- **Both** - changing a `logicalType` or `physicalType`, a `physicalName`, a relationship's target, the column of a `freshness` service level, a vector's `dimensions` or `elementType`, or a column joining or leaving a composite primary key.
- **Undetermined** - changing a `pattern`, a quality rule's query, metric or implementation, or a value the CLI cannot parse.
- **Untested** - descriptions, tags, servers, team, and other metadata; quality rules whose `severity` only warns (`info`, `warning`, `warn`, `low`, `minor`, `trivial`); service levels other than `freshness`, including `retention`.

A change inside an added or removed element has no direction of its own: the element carries the grade.

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