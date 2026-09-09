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

The official ODCS Excel templates ship with the CLI, so the export works offline: one for ODCS v3.0, one for v3.1 and one for v3.2. The export picks the one matching the contract's `apiVersion` — on the major and minor version, so `v3.0.2` and `v3.0.0` both get the v3.0 template. A contract with no `apiVersion`, or one newer than the newest bundled template, gets the newest. For the template structure, see the [ODCS Excel Template repository](https://github.com/datacontract/open-data-contract-standard-excel-template).

Use `--template` to export into your own workbook instead — a local path or a URL:

```bash
datacontract export excel orders.odcs.yaml --template ./my-odcs-template.xlsx --output orders.xlsx
```

You can customize the template as you like.
Start from a copy of the official template and adapt it (branding, extra sheets, additional columns).
Note that if you drop or rename sheet names or column headers, the export will drop the associated information from the contract.

All options: **[`datacontract export excel`](../commands/export/excel.md)**.
