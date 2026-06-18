---
sidebar_position: 26
title: "Export: DQX"
description: "Export a data contract to Databricks DQX checks."
---

<img className="page-icon" src="/img/icons/databricks.svg" alt="" />

# Export: DQX

Converts the contract's [quality rules](../quality-rules/index.md) to [Databricks DQX](https://databrickslabs.github.io/dqx/) checks.

```bash
datacontract export dqx user_interactions.odcs.yaml --schema-name user_interactions
```

Running this against the [example `user_interactions` contract](https://github.com/datacontract/datacontract-cli/blob/main/examples/user_interactions/user_interactions.odcs.yaml) produces:

```yaml
- criticality: error
  check:
    function: is_not_null
    arguments:
      column: interaction_id
- criticality: error
  check:
    function: is_not_null
    arguments:
      column: user_id
- criticality: error
  check:
    function: is_in_list
    arguments:
      allowed:
      - click
      - view
      - purchase
      column: interaction_type
- criticality: warn
  check:
    function: is_in_range
    arguments:
      min_limit: 0
      max_limit: 1000
      column: interaction_value
```
