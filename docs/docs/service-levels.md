---
sidebar_position: 9
title: "Define your Service Levels"
description: "Declare freshness and retention expectations in a data contract with ODCS slaProperties and verify them with datacontract test."
---

# Define your Service Levels

Beyond structure and quality, a data contract can declare **service levels** — the promises a provider makes about *when* the data arrives and *how long* it is kept. In ODCS these live in the top-level `slaProperties` block, and the CLI turns two of them into executable checks:

```yaml
slaProperties:
  - property: freshness
    value: 24
    unit: h
    element: orders.order_timestamp
  - property: retention
    value: P1Y
    element: orders.order_timestamp
```

Run them with [`datacontract test`](./testing/index.md) like any other check:

```bash
datacontract test --checks servicelevel datacontract.yaml
```

Omit `--checks` to run service levels alongside the schema and quality checks.

## Freshness

**`property: freshness`** asserts that the data is recent. The CLI reads the **newest** value of the referenced timestamp column (`MAX`) and compares its age against the threshold:

```yaml
slaProperties:
  - property: freshness
    value: 24
    unit: h
    element: orders.order_timestamp
```

> Passes when `now − MAX(orders.order_timestamp) < 24 hours`.

| Freshness unit | Meaning |
|---|---|
| `d`, `day`, `days` | days (the default when `unit` is omitted) |
| `h`, `hr`, `hour`, `hours` | hours |
| `m`, `min`, `minute`, `minutes` | minutes |

## Retention

**`property: retention`** asserts the opposite end: that data older than the retention period has been deleted. The CLI reads the **oldest** value of the column (`MIN`) and compares its age against the threshold:

```yaml
slaProperties:
  - property: retention
    value: 1
    unit: y
    element: orders.order_timestamp
```

> Passes when `now − MIN(orders.order_timestamp) < 1 year`.

| Retention unit | Meaning |
|---|---|
| `y`, `yr`, `year`, `years` | years (365 days) |
| `m`, `mo`, `month`, `months` | months (30 days) |
| `d`, `day`, `days` | days (the default when `unit` is omitted) |
| `h`, `hr`, `hour`, `hours` | hours |
| `min`, `minute`, `minutes` | minutes |
| `s`, `sec`, `second`, `seconds` | seconds |

:::caution
`unit: m` means **minutes** for `freshness` but **months** for `retention`. Spell the unit out (`minutes` / `months`) if you want to be unambiguous.
:::

Retention also accepts an **ISO 8601 duration** as the `value`, in which case `unit` is ignored:

```yaml
slaProperties:
  - property: retention
    value: P1Y6M      # 1 year and 6 months; also P7Y, P90D, P12W, PT48H
    element: orders.order_timestamp
```

## The `element` reference

`element` must be a **fully qualified `schema.property`** reference — exactly one dot — pointing at a date or timestamp column:

```yaml
element: orders.order_timestamp   # schema "orders", property "order_timestamp"
```

Timestamps without a timezone are interpreted as UTC, and the age is measured against the current UTC time.

:::note
ODCS also defines a contract-level `slaDefaultElement`. The CLI does not use it — spell out `element` on every SLA property that should be checked.
:::

## When no check is generated

A service level is skipped — without failing the run — when:

- the `property` is anything other than `freshness` or `retention` (for example `latency`, `frequency`, or `timeOfAvailability`, which are documentation only),
- `element` or `value` is missing,
- `element` is not exactly one `schema.property` reference,
- the referenced schema is not in the contract,
- the `unit` is not one of the values listed above, or
- the `value` is a string that is not a supported ISO 8601 duration.

Run with `--debug` to see the reasons. If the check *does* run but the column is empty or entirely `NULL`, the check **fails** with `No timestamp value found in '<field>'`.

## Where service levels are used

- **[`test`](./commands/test.md)** — `freshness` and `retention` run as `servicelevel` checks.
- **[SodaCL export](./exports/sodacl.md)** — both become Soda freshness and retention checks.
- **[Markdown](./exports/markdown.md)**, **[HTML](./exports/html.md)**, and **[Excel](./exports/excel.md)** exports render the full `slaProperties` block, including the properties that are documentation only, and the `customProperties` and `authoritativeDefinitions` an entry may carry since ODCS v3.2.0.
- **[`changelog`](./commands/changelog.md)** reports added, removed, and changed service levels between two versions.

## Learn more

- The full `slaProperties` syntax is part of the [Open Data Contract Standard](https://bitol-io.github.io/open-data-contract-standard/latest/).
- The [`orders` example contract](https://github.com/datacontract/datacontract-cli/blob/main/examples/orders/orders.odcs.yaml) declares both a freshness and a retention SLA.
