---
sidebar_position: 6
title: "Export: Avro"
description: "Export a data contract to an Avro schema, with custom logicalType and default support."
---

# Export: Avro

Converts the data contract into an Avro schema. It supports specifying custom Avro properties for logical types and default values.

```bash
datacontract export avro datacontract.yaml --output schema.avsc
```

## Custom Avro properties

A **config map on field level** may include additional key-value pairs. At the moment, [`logicalType`](https://avro.apache.org/docs/1.11.0/spec.html#Logical+Types) and `default` are supported.

```yaml
models:
  orders:
    fields:
      my_field_1:
        description: Example for AVRO with Timestamp (microsecond precision)
        type: long
        example: 1672534861000000  # 2023-01-01 01:01:01 in microseconds
        required: true
        config:
          avroLogicalType: local-timestamp-micros
          avroDefault: 1672534861000000
```

- `avroLogicalType` — the Avro logical type of the field (here `local-timestamp-micros`).
- `avroDefault` — the default value for the field in Avro.
