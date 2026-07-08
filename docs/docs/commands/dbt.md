---
sidebar_position: 6
title: "dbt"
description: "Generate dbt tests from a contract and run them."
---

# `datacontract dbt`

Work with data contracts in your dbt project.

- `datacontract dbt sync` — merge an ODCS contract's schema (columns, descriptions, tags) and tests into your dbt project.
- `datacontract dbt test` — run the generated, contract-managed tests.

See the [dbt Integration](../dbt.md) guide.

## `datacontract dbt sync`

Merge one or more ODCS contracts' schema (column data types, descriptions, tags, model metadata) and tests into your dbt project. Modifies the existing dbt model YAML in place (preserving comments and formatting) and, if needed, creates a new model YAML sidecar (next to a model's `.sql`) or singular SQL tests (under `<test-paths>/datacontract_cli/`).

```bash
datacontract dbt sync [CONTRACT] ...
```

| Argument | Description |
|---|---|
| `CONTRACT` | One or more paths or globs of ODCS contracts to sync. If omitted, every `*.odcs.yaml` under `--project-dir` (and its subdirectories) is synced. |

| Option                                         | Default                                       | Description |
|------------------------------------------------|-----------------------------------------------|---|
| `--project-dir`                                | current dir                                   | Path to the dbt project root (must contain `dbt_project.yml`). |
| `--schema-name`                                | `all`                                         | Which ODCS schema to sync, by name. |
| `--model-resolution`                           | `name`                                        | Map an ODCS schema to a dbt model name: `name` or `physicalName`. |
| `--prune` / `--no-prune`                       | `--no-prune`                                  | Remove model columns and tags that are not declared in the contract. |
| `--target`                                     | —                                             | Forwarded to `dbt test --target`. |
| `--profiles-dir`                               | —                                             | Forwarded to `dbt test --profiles-dir`. |
| `--run-tests` / `--skip-tests`                 | `--skip-tests`                                | Run `dbt test` after syncing (requires dbt installed and on PATH). Required by `--publish`/`--server`. |
| `--publish`                                    | —                                             | URL to publish the results to. |
| `--server`                                     | The only one in the contract, else `--target` | Selected ODCS server. Its `type` is the dialect for mapping the contract's types to column `data_type`s, and its name is used for published results. |
| `--ssl-verification` / `--no-ssl-verification` | `--ssl-verification`                          | SSL verification when publishing. |
| `--debug` / `--no-debug`                       | `--no-debug`                                  | Enable debug logging. |

```bash
datacontract dbt sync orders.odcs.yaml --project-dir ./warehouse
```

### Example

Given this contract for IDs and email addresses in the `orders` schema:

```yaml title="orders-v1.odcs.yaml"
apiVersion: v3.0.0
kind: DataContract
id: orders
version: 1.0.0
status: active
schema:
  - name: orders
    description: Customer orders
    properties:
      - name: order_id
        physicalType: integer
        primaryKey: true
      - name: customer_email
        description: Billing email address
        logicalType: string
        physicalType: text
        required: true
        logicalTypeOptions:
          maxLength: 320
```

Let's assume that a minimal model properties file already exists. This is what it looks like after running
`datacontract dbt sync orders-v1.odcs.yaml` (highlighted lines got added):

```yaml title="models/orders.yml" {5-8,12-37,41-55}
version: 2
models:
  - name: orders
    description: Customer orders
    config:
      meta:
        datacontract_cli:
          contract_id: orders
    columns:
      - name: order_id
        data_type: integer
        data_tests:
          - not_null:
              config:
                severity: warn
                meta:
                  datacontract_cli:
                    check: orders__order_id__field_required
                    include_in_tests: true
                    contract_versions:
                      - 1.0.0
                    generated: true
              description: Check that field order_id has no missing values
          - unique:
              config:
                severity: warn
                meta:
                  datacontract_cli:
                    check: orders__order_id__field_unique
                    include_in_tests: true
                    contract_versions:
                      - 1.0.0
                    generated: true
              description: Check that field order_id has no duplicate values
        meta:
          datacontract_cli:
            generated: true
      - name: customer_email
        data_type: text
        description: Billing email address
        data_tests:
          - not_null:
              config:
                severity: warn
                meta:
                  datacontract_cli:
                    check: orders__customer_email__field_required
                    include_in_tests: true
                    contract_versions:
                      - 1.0.0
                    generated: true
              description: Check that field customer_email has no missing values
        meta:
          datacontract_cli:
            generated: true
```

The generated `config.meta.datacontract_cli` block is how `dbt sync`/`dbt test` recognize and scope managed tests; the per-column `meta.datacontract_cli.generated` marks a column the CLI added.

The `maxLength` bound becomes a self-contained singular SQL test (no `dbt_utils` needed). Its `config()` header carries the same `datacontract_cli` metadata:

```sql title="tests/datacontract_cli/orders/orders__1_0_0__orders__customer_email__length.sql"
-- AUTO-GENERATED by `datacontract dbt sync`. Do not edit.
-- Source contract: orders@1.0.0 (model: orders, check: customer_email__length)
{{ config(severity='warn', meta={"datacontract_cli": {"check": "orders__customer_email__field_length", "contract_versions": ["1.0.0"], "generated": true, "include_in_tests": true, "model": "orders", "field": "customer_email", "description": "Check that field customer_email has a length of at most 320"}}) }}
SELECT *
FROM {{ ref('orders') }}
WHERE "customer_email" IS NOT NULL
  AND (LENGTH("customer_email") > 320)
```

## `datacontract dbt test`

Run the contract-managed dbt tests that `datacontract dbt sync` generated, scoped to the requested contracts' models, report the results, and optionally publish them. Never modifies project files — run `datacontract dbt sync` first to (re)generate the tests. With multiple contracts, each contract's results are reported (and published) separately, followed by a summary.

```bash
datacontract dbt test [CONTRACT]...
```

| Argument | Description |
|---|---|
| `CONTRACT` | One or more paths or globs of ODCS contracts to test. If omitted, every `*.odcs.yaml` under `--project-dir` (and its subdirectories) is tested. Non-ODCS files are skipped with a warning, and a glob that matches nothing is ignored. |

| Option | Default | Description |
|---|---|---|
| `--project-dir` | current dir | Path to the dbt project root (must contain `dbt_project.yml`). |
| `--target` | — | Forwarded to `dbt test --target`. |
| `--profiles-dir` | — | Forwarded to `dbt test --profiles-dir`. |
| `--publish` | — | URL to publish the results to. |
| `--server` | The only one in the contract, else `--target` | ODCS server name for published test results. |
| `--ssl-verification` / `--no-...` | on | SSL verification when publishing. |
| `--debug` / `--no-debug` | off | Enable debug logging. |

```bash
datacontract dbt test orders.odcs.yaml --project-dir ./warehouse
```
