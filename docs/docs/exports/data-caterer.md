---
sidebar_position: 24
title: "Export: Data Caterer"
description: "Export a data contract to a Data Caterer data-generation task."
---

<img className="page-icon" src="/img/icons/generic.svg" alt="" />

# Export: Data Caterer

Converts the data contract to a data-generation task in YAML that can be ingested by [Data Caterer](https://github.com/data-catering/data-caterer). This lets you generate production-like data in any environment based on your contract.

```bash
datacontract export data-caterer datacontract.yaml --schema-name orders
```

You can further customize generation by adding [additional metadata in the YAML](https://data.catering/setup/generator/data-generator/).
