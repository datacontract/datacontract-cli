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

## Templates

The official ODCS Excel template ships with the CLI, so the export works offline. For the template structure, see the [ODCS Excel Template repository](https://github.com/datacontract/open-data-contract-standard-excel-template).

Use `--template` to export into your own workbook instead — a local path or a URL:

```bash
datacontract export excel orders.odcs.yaml --template ./my-odcs-template.xlsx --output orders.xlsx
```

A custom template must keep the sheets and named ranges of the official template, as those are what the export fills in. Start from a copy of the official template and adapt it (branding, extra sheets, additional columns).

All options: **[`datacontract export excel`](../commands/export/excel.md)**.
