---
sidebar_position: 28
title: "Export: Custom (Jinja)"
description: "Export a data contract to any format using a custom Jinja template."
---

<img className="page-icon" src="/img/icons/custom.svg" alt="" />

# Export: Custom (Jinja)

Converts the data contract into any custom format using a [Jinja](https://jinja.palletsprojects.com/) template. Specify the template path with `--template`.

```bash
datacontract export custom --template template.txt datacontract.yaml
```

## Template variables

You can use the ODCS object directly. `data_contract` is an `OpenDataContractStandard` instance; top-level fields include `name`, `id`, `version`, `schema_` (the list of schemas), `servers`, `team`, etc.

```text
title: {{ data_contract.name }}
schemas:
{%- for schema in data_contract.schema_ %}
  - name: {{ schema.name }}
{%- endfor %}
```

```bash
$ datacontract export custom --template template.txt datacontract.yaml
title: Orders Latest
schemas:
  - name: orders
```

## Per-schema templates

Add `--schema-name` to render a single schema. The template then also receives:

- `schema_name` (str)
- `schema` (the `SchemaObject` from ODCS)

```bash
datacontract export custom datacontract.odcs.yaml --template template.sql --schema-name orders
```
