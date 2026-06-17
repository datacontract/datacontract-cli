---
sidebar_position: 7
title: "ci"
description: "Run tests for CI/CD pipelines with annotations and summaries."
---

# `datacontract ci`

Run tests for CI/CD pipelines. Wraps [`test`](./test.md) with CI-specific features: GitHub Actions annotations and step summary, Azure DevOps annotations, machine-readable output, and exit-code control. See [Scheduling](../scheduling.md) for full pipeline examples.

```bash
datacontract ci [LOCATIONS]...
```

| Argument | Description |
|---|---|
| `LOCATIONS...` | One or more locations (URL or path) of contract files. Supports globs, e.g. `contracts/*.yaml`. |

| Option | Default | Description |
|---|---|---|
| `--server` | `all` | Which server to test, or `all`. |
| `--publish` | — | URL to publish the results to. |
| `--output` | — | File path to write results to. |
| `--output-format` | — | `json` or `junit`. |
| `--json` | — | Print test results as JSON to stdout. |
| `--fail-on` | `error` | Minimum severity that causes a non-zero exit: `warning`, `error`, or `never`. |
| `--logs` / `--no-logs` | `--no-logs` | Print logs. |
| `--ssl-verification` / `--no-...` | on | SSL verification when publishing. |
| `--inline-references` / `--no-...` | on | Resolve and inline external references. |
| `--debug` / `--no-debug` | off | Enable debug logging. |

```bash
datacontract ci datacontract.yaml --output test-results.xml --output-format junit
```
