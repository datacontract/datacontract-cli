---
sidebar_position: 27
title: "Export: Excel"
description: "Export a data contract to an ODCS Excel template."
---

# Export: Excel

Converts a data contract into an ODCS Excel template — a user-friendly spreadsheet for authoring, sharing, and managing data contracts.

```bash
datacontract export excel datacontract.yaml --output datacontract.xlsx
```

The Excel format enables:

- **User-friendly authoring** in Excel's familiar interface.
- **Easy sharing** as standard Excel files.
- **Collaboration** with non-technical stakeholders.
- **Round-trip conversion** back to YAML via [`import excel`](../imports/excel.md).

For the template structure, see the [ODCS Excel Template repository](https://github.com/datacontract/open-data-contract-standard-excel-template).
