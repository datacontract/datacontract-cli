---
sidebar_position: 14
title: "Best Practices"
description: "Recommended workflows for adopting data contracts: the data-first and contract-first approaches."
---

# Best Practices

There are two proven ways to introduce data contracts with the Data Contract CLI. Pick the one that matches your situation.

## Data-first approach

Create a data contract based on the **actual data**. This is the fastest way to get started and to get feedback from data consumers.

1. Use an existing physical schema (e.g. SQL DDL) as a starting point to define your logical data model in the contract. Right after the import, double-check that the actual data meets the imported model:

   ```bash
   datacontract import sql --source ddl.sql
   datacontract test
   ```

2. Add [quality checks](./quality-rules/index.md) and additional type constraints one by one, making sure the data still adheres to the contract:

   ```bash
   datacontract test
   ```

3. Validate that the `datacontract.yaml` is correctly formatted and adheres to the [Open Data Contract Standard](./open-data-contract-standard.md):

   ```bash
   datacontract lint
   ```

4. Set up a CI pipeline that runs daily for continuous quality checks. Use the [`ci`](./commands/ci.md) command for CI-optimized output (GitHub Actions annotations and step summary, Azure DevOps annotations). You can also report results to tools like [Entropy Data](https://entropy-data.com):

   ```bash
   datacontract ci --publish https://api.entropy-data.com/api/test-results
   ```

   See [Test your contract → Scheduling and CI/CD](./testing.md#scheduling-and-cicd).

## Contract-first approach

Create a data contract based on the **requirements** from use cases, before the data product exists.

1. Start with a `datacontract.yaml` template:

   ```bash
   datacontract init
   ```

2. Create the model and quality guarantees based on your business requirements. Fill in the terms, descriptions, etc., then validate the format:

   ```bash
   datacontract lint
   ```

3. Use the [export](./exports/index.md) functions to start building the providing data product as well as the integration into consuming data products:

   ```bash
   # data provider
   datacontract export dbt-models
   # data consumer
   datacontract export dbt-sources
   datacontract export dbt-staging-sql
   ```

4. Test that your data product implementation adheres to the contract:

   ```bash
   datacontract test
   ```
