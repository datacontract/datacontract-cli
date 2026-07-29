---
sidebar_position: 28
title: "FAQ"
description: "Short answers to the questions that come up most often when working with the Data Contract CLI."
---

# FAQ

## Which contract format should I use?

[ODCS](./open-data-contract-standard.md). The older Data Contract Specification (`models`/`fields`) is still read, but write new contracts in ODCS — see [Migrate from DCS to ODCS](./migrate-dcs-to-odcs.md).

## I imported a contract and `test` immediately fails on types. Why?

On the nine backends with catalog introspection, the declared `physicalType` is compared against the column's real native type — a stricter check than the portable `logicalType` used elsewhere. See [Types](./schema.md#types) and the [Data Source Reference](./reference/index.md#how-data-types-work).

## I set `isNullable: false` but nothing is checked.

The CLI reads `required`, not `isNullable`. Write `required: true`. See [What is not checked](./schema.md#what-is-not-checked).

## Where do credentials go?

Never in the contract. Connection details live in `servers`; credentials come from environment variables or a `.env` file in the working directory. Each [reference page](./reference/index.md) lists the variables its source expects.

## How do I make CI fail on quality warnings?

`datacontract ci --fail-on warning`. The default is `error`; `never` always exits 0. See [`ci`](./commands/ci.md).

## How do I run only some checks?

`--checks schema`, `quality`, or `servicelevel`, comma-separated. Omit it to run everything. See [Test your Data](./testing/index.md).

## Which optional dependency do I need?

One per data source — `datacontract-cli[snowflake]`, `[databricks]`, `[postgres]`, … — or `[all]` for everything. See [Installation](./installation.md#optional-dependencies-extras).

## TLS fails behind a corporate proxy.

Use `datacontract --system-truststore …` to verify against the operating system's trust store instead of the bundled CA certificates, or set `DATACONTRACT_SYSTEM_TRUSTSTORE=1`.

## Can I use it without the CLI?

Yes — as a [Python library](./python-library.md), or as a REST service with [`datacontract api`](./api.md).

## Something is missing or broken.

Open an [issue on GitHub](https://github.com/datacontract/datacontract-cli/issues) or ask in the [community Slack](https://datacontract.com/slack). To add it yourself, see [Contributing](./contributing.md).
