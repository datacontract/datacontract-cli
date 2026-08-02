---
sidebar_position: 2
title: "GitHub Actions"
description: "Test data contracts in pull requests and on a cron schedule with GitHub Actions, with annotations, job summaries, and secrets-based credentials."
---

# GitHub Actions

Run data contract tests in the same workflow twice over: on every change (push and pull request), so a breaking change is caught in the PR that introduces it, and on a cron schedule, so data drift in production is caught between changes.

The quickest route is the ready-made **[datacontract/datacontract-action](https://github.com/datacontract/datacontract-action/)**. To run the CLI directly:

```yaml
# .github/workflows/datacontract.yml
name: Data Contract CI

on:
  push:
    branches: [main]
  pull_request:
  schedule:
    # Run every day at 06:00 UTC to catch data drift in production
    - cron: "0 6 * * *"

jobs:
  datacontract-ci:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install datacontract-cli
      # Test one or more data contracts (supports globs, e.g. contracts/*.yaml)
      - run: datacontract ci datacontract.yaml
        env:
          DATACONTRACT_POSTGRES_USERNAME: ${{ secrets.DB_USERNAME }}
          DATACONTRACT_POSTGRES_PASSWORD: ${{ secrets.DB_PASSWORD }}
```

## What `ci` does in Actions

The [`ci`](../commands/ci.md) command detects GitHub Actions and emits:

- **Annotations** on failed checks, so violations show up inline in the PR.
- A **job summary** with the check results as markdown.
- A nonzero **exit code** on violations, failing the workflow; tune with `--fail-on error|warning|never` (see [controlling failure behavior](./index.md#controlling-failure-behavior)).

## Credentials

Pass credentials for the server under test as [configuration environment variables](../configuration.md) from GitHub secrets, as in the example above (`DATACONTRACT_POSTGRES_USERNAME`, `DATACONTRACT_SNOWFLAKE_PASSWORD`, …). Each data source's variables are listed in [Test your Data](../testing/index.md).

## Publishing results

Add `--publish` to track results centrally:

```yaml
      - run: datacontract ci datacontract.yaml --publish https://api.entropy-data.com/api/test-results
        env:
          ENTROPY_DATA_API_KEY: ${{ secrets.ENTROPY_DATA_API_KEY }}
```

See [Integrate with Entropy Data](../entropy-data.md).
