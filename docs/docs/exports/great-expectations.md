---
sidebar_position: 23
title: "Export: Great Expectations"
description: "Export a data contract to a Great Expectations suite."
---

# Export: Great Expectations

Transforms a data contract into a comprehensive [Great Expectations](https://greatexpectations.io/) JSON suite. If the contract includes multiple models, specify the model with `--schema-name`.

```bash
datacontract export great-expectations datacontract.yaml --schema-name orders
```

The export builds expectations from the model definition (with a fixed mapping) and from the `quality` rules of each model (see the [expectations gallery](https://greatexpectations.io/expectations/)).

## Additional options

- `suite_name` — the name of the expectation suite. Defaults to a name derived from the model name(s).
- `engine` — the execution engine: `pandas` (in-memory dataframes), `spark` (Spark dataframes), or `sql` (SQL databases).
- `sql_server_type` — the SQL server type to connect with when `engine` is `sql`. Ensures the correct SQL dialect and connection settings are applied.
