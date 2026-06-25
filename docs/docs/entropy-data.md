---
sidebar_position: 17
title: "Integrate with Entropy Data"
description: "Publish data contract test results to Entropy Data, a commercial platform for managing data contracts."
---

# Integrate with Entropy Data

[Entropy Data](https://entropy-data.com/) is a commercial platform to manage data contracts. It provides a web UI, access management, and data governance for a data product marketplace based on data contracts.

The Data Contract CLI integrates with Entropy Data through the `--publish` option: it runs the tests and pushes the **full results** to the [Entropy Data API](https://api.entropy-data.com/swagger/index.html), where they are displayed and tracked over time.

## Publish test results

Reference the contract by URL, run the tests against a server, and append `--publish`. Provide your API key as an environment variable.

```bash
export ENTROPY_DATA_API_KEY=xxx

datacontract test https://demo.entropy-data.com/demo279750347121/datacontracts/4df9d6ee-e55d-4088-9598-b635b2fdcbbc/datacontract.yaml \
  --server production \
  --publish https://api.entropy-data.com/api/test-results
```

The same `--publish` option is available on [`ci`](./commands/ci.md) and [`dbt sync`](./commands/dbt.md), so you can report results from CI/CD and scheduled runs — see [Test your contract → Scheduling and CI/CD](./testing.md#scheduling-and-cicd).

## Publish the contract

Use the [`publish`](./commands/publish.md) command to push a data contract itself to Entropy Data:

```bash
datacontract publish datacontract.yaml
```

## TLS behind a corporate proxy or internal CA

By default the CLI verifies TLS certificates against the bundled CA certificates (`certifi`). In a corporate network with a TLS-inspecting proxy or an internal certificate authority, this can fail with `CERTIFICATE_VERIFY_FAILED: unable to get local issuer certificate`, because the root CA is installed in the operating system's trust store but not in the bundled list.

Use the global `--system-truststore` option to verify against the operating system's trust store (macOS Keychain, Windows certificate store, or the system CA certificates on Linux) instead:

```bash
datacontract --system-truststore publish datacontract.yaml
```

You can also enable it for every invocation with an environment variable:

```bash
export DATACONTRACT_SYSTEM_TRUSTSTORE=1
```

This keeps certificate verification on while trusting the corporate root CA. It works for all commands that make HTTPS requests, not only the Entropy Data integration.
