---
sidebar_position: 0
title: "Commands"
slug: /commands
description: "Reference for every Data Contract CLI command."
---

# Commands

The `datacontract` CLI groups its functionality into the following commands. Run `datacontract --help` or `datacontract <command> --help` at any time to see the latest usage.

| Command | Description |
|---|---|
| [`init`](./init.md) | Create an empty data contract from a template. |
| [`edit`](./edit.md) | Edit a contract in the Data Contract Editor (web UI). |
| [`lint`](./lint.md) | Validate that the contract is correctly formatted. |
| [`changelog`](./changelog.md) | Show a changelog between two contracts. |
| [`test`](./test.md) | Run schema and quality tests on configured servers. |
| [`dbt`](./dbt.md) | Generate dbt tests from a contract and run them (`dbt sync`). |
| [`ci`](./ci.md) | Run tests for CI/CD pipelines with annotations and summaries. |
| [`export`](./export.md) | Convert a contract to a target format. |
| [`import`](./import.md) | Create a contract from a source format. |
| [`catalog`](./catalog.md) | Create an HTML catalog of data contracts. |
| [`publish`](./publish.md) | Publish a contract to Entropy Data. |
| [`api`](./api.md) | Start the CLI as a web server with a REST API. |

## Common usage

```bash
datacontract init odcs.yaml
datacontract edit odcs.yaml
datacontract lint odcs.yaml
datacontract changelog v1.odcs.yaml v2.odcs.yaml
datacontract test odcs.yaml
datacontract dbt sync orders.odcs.yaml --project-dir ./warehouse
datacontract export html datacontract.yaml --output odcs.html
datacontract import sql --source my-ddl.sql --dialect postgres --output odcs.yaml
```

Most commands accept a `--debug` flag for verbose logging.
