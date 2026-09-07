---
sidebar_position: 12
title: "Export: Excel"
description: "Export a data contract to an ODCS Excel template."
---

# <img className="page-icon" src="/img/icons/excel.svg" alt="" /> Export: Excel

Converts a data contract into an ODCS Excel template — a user-friendly spreadsheet for authoring, sharing, and managing data contracts.

```bash
datacontract export excel orders.odcs.yaml --output orders.xlsx
```

Running this against the [example `orders` contract](https://github.com/datacontract/datacontract-cli/blob/main/examples/orders/orders.odcs.yaml) produces an `orders.xlsx` workbook with the ODCS template sheets — fundamentals, servers, the `orders` and `line_items` schemas, quality, and service levels — pre-filled from the contract.

The Excel format enables:

- **User-friendly authoring** in Excel's familiar interface.
- **Easy sharing** as standard Excel files.
- **Collaboration** with non-technical stakeholders.
- **Round-trip conversion** back to YAML via [`import excel`](../imports/excel.md).

## Workbook layout

One sheet per section of the contract: `Fundamentals`, one `Schema <name>` sheet per schema, `Relationships`, `Quality`, `Support`, `Team`, `Roles`, `SLA`, `Servers`, `Pricing`, and — for ODCS v3.2 — `Enum`, `Synonyms`, `Verified Statements`, `Constraints`, `Custom Properties` and `Authoritative Definitions`.

Elements that belong to a row of another sheet name their owner with an **element reference**: an `Element Type` (`Schema`, `Property`, `Server`, `Quality`, `Enum Value`, …) and an `Element`, which is the owner's natural key — a schema's name, a property's dotted path such as `orders.address.street`, a server's `server`, a support channel's `channel`, a team member's `username`, an enum value as `orders.status=shipped`, a synonym as `orders=Bestellungen` — or its `id` where it has no natural key (quality rules, relationships, verified statements, constraints). An element whose key is missing or duplicated cannot be referenced: its rich custom properties and authoritative definitions are dropped with a warning asking for an `id`. The export never generates ids.

### Custom properties

A custom property that carries only a `property` and a scalar `value` is written **inline**, in a `Custom Property` / `Custom Value` column pair at the right of its owner's row (or as a row pair below a schema's header block and below the server block). The export adds as many pairs as the contract needs. A custom property with an `id`, `description` or `vendor`, or whose value would not survive a plain cell — a list, an object, or a string such as `"true"`, `"007"` or `"3.10"` that Excel would read back as something else — goes to the `Custom Properties` sheet instead, with a `Type` of `Text` (verbatim string) or `JSON` (array or object). The contract's own custom properties always live on that sheet, except `owner`, which fills the `Owner` cell on `Fundamentals`.

The same rule applies to authoritative definitions: a property's first plain definition stays in the `Authoritative Definition URL` / `Type` columns of the schema sheet, everything else goes to the `Authoritative Definitions` sheet.

### Servers

The `Servers` sheet has one generic block with every ODCS server field; the fields that do not apply to the selected `Type` are greyed out, for all ODCS server types.

## Templates

The official ODCS Excel template ships with the CLI, so the export works offline. For the template structure, see the [ODCS Excel Template repository](https://github.com/datacontract/open-data-contract-standard-excel-template).

Use `--template` to export into your own workbook instead — a local path or a URL:

```bash
datacontract export excel orders.odcs.yaml --template ./my-odcs-template.xlsx --output orders.xlsx
```

A custom template must keep the sheets and named ranges of the official template, as those are what the export fills in. Start from a copy of the official template and adapt it (branding, extra sheets, additional columns). A template made from an earlier version of the official one still works: the export never fails on it, but logs a single warning listing what the template cannot hold — enum values, synonyms, rich custom properties, ids — and which `templateVersion` would keep them.

All options: **[`datacontract export excel`](../commands/export/excel.md)**.
