---
sidebar_position: 21
title: "Export: Iceberg"
description: "Export a data contract to an Apache Iceberg schema."
---

<img className="page-icon" src="/img/icons/generic.svg" alt="" />

# Export: Iceberg

Exports to an [Iceberg Table JSON Schema Definition](https://iceberg.apache.org/spec/#appendix-c-json-serialization).

This export supports a single model at a time, because Iceberg's schema definition is for a single table (1 model → 1 table). Use `--schema-name` to select the model.

```bash
datacontract export iceberg --schema-name orders datacontract.yaml --output orders_iceberg.json
```

```json
{
  "type": "struct",
  "fields": [
    { "id": 1, "name": "order_id", "type": "string", "required": true },
    { "id": 2, "name": "order_timestamp", "type": "timestamptz", "required": true }
  ],
  "schema-id": 0,
  "identifier-field-ids": [1]
}
```
