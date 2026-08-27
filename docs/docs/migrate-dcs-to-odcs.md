---
sidebar_position: 23
title: "Migrate from DCS to ODCS"
description: "Convert a Data Contract Specification (datacontract.yaml) file to the Open Data Contract Standard with one command, and verify the conversion was lossless."
---

# Migrate from DCS to ODCS

Contracts that start with `dataContractSpecification:` and describe their structure under
`models:`/`fields:` use the **Data Contract Specification (DCS)**, the format the CLI was
originally built around. The CLI now uses the
**[Open Data Contract Standard (ODCS)](./open-data-contract-standard.md)** natively.

:::note[Your DCS contracts keep working]
`lint`, `test`, and `export` detect a DCS file and convert it in memory before doing their work.
Migrating just makes the ODCS version the file you keep in Git.
:::

## Convert

```bash
datacontract export odcs datacontract.yaml --output datacontract.odcs.yaml
```

For a whole repository of contracts:

```bash
find . -name 'datacontract.yaml' -exec sh -c \
  'datacontract export odcs "$1" --output "$(dirname "$1")/datacontract.odcs.yaml"' _ {} \;
```

## Verify

```bash
# 1. The new file is valid ODCS.
datacontract lint datacontract.odcs.yaml

# 2. Nothing changed semantically — both files are compared as ODCS,
#    so an empty table means the conversion was lossless.
datacontract changelog datacontract.yaml datacontract.odcs.yaml

# 3. The new file still passes against real data.
datacontract test datacontract.odcs.yaml
```

Once all three pass, delete the DCS file and point your [CI/CD pipeline](./scheduling/index.md) at the new
one.

## Three things to check by hand

- **`status` defaults to `draft`** when the DCS file has no `info.status`. Change it to
  `active` (or another value) once the contract is ready for production.
- **The deprecated `primary: true` is not carried over** — only `primaryKey: true` is. Search
  your contracts for `primary:` and set `primaryKey: true` in the ODCS file.
- **`physicalType` holds the DCS `type`**, so a column reads `physicalType: string` instead of
  its native type. Replace it with the real type (`VARCHAR`, `NUMBER(12,2)`, …) or drop it and
  keep only `logicalType`.

Everything else is mapped automatically: `models` → `schema`, `fields` → `properties`,
`servicelevels` → `slaProperties`, `terms` → `description`, `field.enum` → a
[quality rule](./quality-rules/index.md), `$ref` definitions inlined. Anything without an ODCS
equivalent (contact details, Kafka `topic`, `pii`, `precision`) is preserved under
`customProperties`.

## Going back

[`datacontract export dcs`](./exports/dcs.md) converts the other way, if a downstream tool still
expects DCS:

```bash
datacontract export dcs datacontract.odcs.yaml --output datacontract.yaml
```
