---
sidebar_position: 5
title: "Export: dbt Staging SQL"
description: "Export a data contract to a dbt staging SQL file."
---

<img className="page-icon" src="/img/icons/generic.svg" alt="" />

# Export: dbt Staging SQL

Generates a dbt staging SQL file that selects the contract's fields.

```bash
datacontract export dbt-staging-sql datacontract.yaml
```

For fully customized staging models, use the [`custom`](./custom.md) exporter with a Jinja template.
