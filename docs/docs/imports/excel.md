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

You can customize the template as you like.
Start from a copy of the official template and adapt it (branding, extra sheets, additional columns).
Note that the import will not read sheets or columns that are named differently than in the template.

All options: **[`datacontract import excel`](../commands/import/excel.md)**.
