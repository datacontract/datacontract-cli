---
sidebar_position: 18
title: "Trino"
description: "Create a data contract from your Trino tables and test the actual data against it."
---

# <img className="page-icon" src="/img/icons/trino.svg" alt="" /> Trino

Test data in Trino.

## 1. Install

```bash
uv tool install --python python3.11 --upgrade 'datacontract-cli[trino]'
```

See [Installation](../installation.md) for pip, pipx, and Docker.

## 2. Set credentials

Create a `.env` file in your working directory (or export the variables):

```bash
# .env
DATACONTRACT_TRINO_USERNAME=trino
DATACONTRACT_TRINO_PASSWORD=mysecretpassword
```

The default is `basic` auth; JWT and OAuth2 are also supported — see the [Trino Reference](../reference/trino.md).

## 3. Create a contract from your tables

Get the DDL of a table (`SHOW CREATE TABLE my_catalog.my_schema.orders;`), save it to a file, and import it. Trino's ANSI-style DDL generally parses well with the `postgres` dialect:

```bash
datacontract import sql --source orders.sql --dialect postgres --output datacontract.yaml
```

The SQL import can't know your connection details, so it writes a `servers` block with placeholder values. Open `datacontract.yaml` and fill in your cluster:

```yaml
servers:
  - server: trino
    type: trino
    host: localhost
    port: 8080
    catalog: my_catalog
    schema: my_schema
```

## 4. Test the actual data

```bash
datacontract test datacontract.yaml
```

```
🟢 data contract is valid. Run 24 checks. Took 4.4 seconds.
```

## 5. Let it catch a violation

The contract becomes valuable when it detects drift. Tighten an expectation — for example, add a quality rule to a schema in `datacontract.yaml`:

```yaml
schema:
  - name: orders
    # ...
    quality:
      - type: sql
        description: No order has a negative total
        query: SELECT COUNT(*) FROM orders WHERE order_total < 0
        mustBe: 0
```

Run `datacontract test datacontract.yaml` again: every violation is listed as an error, and the command exits with code `1` — ready for [CI/CD scheduling](../ci-cd.md) so you catch drift before your consumers do.

## Reference

All authentication options (basic, JWT, OAuth2) and the data type handling: **[Trino Reference](../reference/trino.md)**.

## Troubleshooting

- **`401 Unauthorized`** — check the auth mode: password-protected clusters need `basic` credentials over HTTPS; token-based setups need `DATACONTRACT_TRINO_AUTHENTICATION=jwt` and `DATACONTRACT_TRINO_JWT_TOKEN`.
- **`Catalog ... does not exist` / `Schema ... does not exist`** — `catalog` and `schema` in the `servers` block must match `SHOW CATALOGS` / `SHOW SCHEMAS FROM <catalog>`.
