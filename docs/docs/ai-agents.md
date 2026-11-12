---
sidebar_position: 14
title: "Use with AI Coding Agents"
description: "Let Claude Code, Codex, GitHub Copilot, and other coding agents create, test, and evolve data contracts with the Data Contract Skills."
---

# Use with AI Coding Agents

The [Data Contract Skills](https://github.com/datacontract/datacontract-skills) teach coding agents such as Claude Code, OpenAI Codex, and GitHub Copilot CLI to work with data contracts. The agent uses the Data Contract CLI and the [Data Contract Editor](./editor.md) under the hood: it imports schemas, writes descriptions and quality rules, lints until the contract is valid, runs the tests, and explains failing checks.

| Skill | What the agent does |
|---|---|
| Create a Data Contract | Imports a contract from a table, DDL, dbt, Avro, JSON Schema, or Excel, or writes it from requirements, then enriches and lints it. |
| Test a Data Contract | Sets up the connection, runs `datacontract test`, and finds the cause of every failing check. |
| Quality Rules | Adds quality rules and service levels per quality dimension, with thresholds grounded in the data. |
| Breaking Change Check | Runs `changelog` and `breaking` on a changed contract, adds semantic changes, and proposes the version bump. |
| Export a Data Contract | Generates SQL DDL, dbt models and tests, schemas, and model classes, and integrates them into the project. |
| Data Contracts in CI/CD | Sets up lint and breaking-change checks on pull requests and scheduled data tests. |
| Data Contract Editor | Opens the contract in the visual editor while the agent edits the YAML. |

## Install

Claude Code:

```bash
claude plugin marketplace add https://github.com/datacontract/datacontract-skills
claude plugin install datacontract-skills@datacontract-skills
```

OpenAI Codex:

```bash
codex plugin marketplace add https://github.com/datacontract/datacontract-skills
codex plugin add datacontract-skills@datacontract-skills
```

GitHub Copilot CLI:

```bash
copilot plugin marketplace add https://github.com/datacontract/datacontract-skills
copilot plugin install datacontract-skills@datacontract-skills
```

Other agents that support [Agent Skills](https://agentskills.io) can use the `skills/` folder of the repository directly, or reference its `AGENTS.md`.

## Usage

Ask in plain language:

- "Create a data contract for the `orders` table in Snowflake."
- "Test the orders contract against production and tell me why it fails."
- "Is my change to the orders contract breaking?"
- "Generate the dbt models and tests from the contract."

The skills ask before connecting to a data source and never ask for credentials in the chat: set them as [environment variables](./configuration.md) or in a `.env` file.

## Documentation for LLMs

Agents without the skills can still read this documentation in a compact form: [llms.txt](https://cli.datacontract.com/llms.txt) (a link index) and [llms-full.txt](https://cli.datacontract.com/llms-full.txt) (every page in one file).
