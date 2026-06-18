---
sidebar_position: 28
title: "Export: Custom (Jinja)"
description: "Export a data contract to any format using a custom Jinja template."
---

<img className="page-icon" src="/img/icons/generic.svg" alt="" />

# Export: Custom (Jinja)

Converts the data contract into any custom format using a [Jinja](https://jinja.palletsprojects.com/) template. Specify the template path with `--template`.

```bash
datacontract export custom --template template.txt orders.odcs.yaml
```

## Template variables

You can use the ODCS object directly. `data_contract` is an `OpenDataContractStandard` instance; top-level fields include `name`, `id`, `version`, `schema_` (the list of schemas), `servers`, `team`, etc.

Given this `template.txt`:

```text
title: {{ data_contract.name }}
schemas:
{%- for schema in data_contract.schema_ %}
  - name: {{ schema.name }}
{%- endfor %}
```

Running it against the [example `orders` contract](https://github.com/datacontract/datacontract-cli/blob/main/examples/orders/orders.odcs.yaml) produces:

```text
title: Orders
schemas:
  - name: orders
  - name: line_items
```

## Per-schema templates

Add `--schema-name` to render a single schema. The template then also receives:

- `schema_name` (str)
- `schema` (the `SchemaObject` from ODCS)

```bash
datacontract export custom datacontract.odcs.yaml --template template.sql --schema-name orders
```
