---
sidebar_position: 12
title: "Import: Excel"
description: "Create a data contract from an ODCS Excel template."
---

# <img className="page-icon" src="/img/icons/excel.svg" alt="" /> Import: Excel

Creates a data contract from an ODCS Excel template — the round-trip counterpart of [`export excel`](../exports/excel.md).

```bash
datacontract import excel --source odcs.xlsx --output datacontract.yaml
```

The import reads every sheet the template has and silently skips the ones it does not: a workbook made from an earlier version of the official template — with per-type server blocks and without the `Enum`, `Synonyms`, `Verified Statements`, `Constraints` or `Authoritative Definitions` sheets — still imports.

## Custom properties

Custom properties are read both from the columns under *Custom Properties (add as needed)* next to an element — the column header is the property name, an empty cell means the row has no such property — and from the `Custom Properties` sheet, and merged. When the same property appears in both places, the sheet wins and a warning is logged.

A value is typed by its cell: a boolean cell is a boolean, a numeric cell a number. A text cell with a blank `Type` is resolved as YAML would resolve it — `true` becomes a boolean, `42` an integer, `007` the integer 7. Set `Type` to `Text` to keep a cell verbatim, or to `JSON` to read an array or object.

Rows on the `Custom Properties`, `Authoritative Definitions`, `Enum` and `Synonyms` sheets that reference an element the workbook does not contain are dropped with a warning naming the row.

All options: **[`datacontract import excel`](../commands/import/excel.md)**.
