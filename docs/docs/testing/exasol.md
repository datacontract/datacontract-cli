---
sidebar_position: 12
title: "Exasol"
description: "Test the actual data in Exasol against your data contract."
---

# <img className="page-icon" src="/img/icons/exasol.svg" alt="" /> Exasol

Test data in Exasol.

## 1. Install

```bash
uv tool install --python python3.11 --upgrade 'datacontract-cli[exasol]'
```

See [Installation](../installation.md) for pip, pipx, and Docker.

## 2. Authenticate

Create a `.env` file in your working directory (or export the variables):

```bash
# .env
DATACONTRACT_EXASOL_USERNAME=sys
DATACONTRACT_EXASOL_PASSWORD=mysecretpassword
```

The server certificate is verified against the system CA store; for a self-signed certificate, pin its fingerprint — see the [Exasol Reference](../reference/exasol.md#tls).

## 3. Describe the server in the contract

The `exasol` server type was added in ODCS v3.2.0, so the contract has to declare
`apiVersion: v3.2.0`. There is no `datacontract import exasol` yet: write the schema by hand, or
start from a DDL script with `datacontract import sql --source orders.sql --dialect postgres` and
replace the generated `servers` block.

```yaml
apiVersion: v3.2.0
kind: DataContract
id: orders
version: 1.0.0
status: active
servers:
  - server: production
    type: exasol
    host: exasol.acme.com
    port: 8563
    schema: sales
schema:
  - name: orders
    properties:
      - name: order_id
        logicalType: integer
        physicalType: DECIMAL(18,0)
        primaryKey: true
      - name: order_total
        logicalType: number
        physicalType: DECIMAL(10,2)
```

`host` may be a cluster range (`n11..14.acme.com`).

## 4. Test the actual data

```bash
datacontract test datacontract.yaml
```

```
Testing datacontract.yaml
Server: production (type=exasol, host=exasol.acme.com, port=8563, schema=sales)
╭────────┬───────────────────────────────────────────────────────────┬──────────┬─────────╮
│ Result │ Check                                                     │ Field    │ Details │
├────────┼───────────────────────────────────────────────────────────┼──────────┼─────────┤
│ passed │ Check that field 'order_id' is present                    │ order_id │         │
│ passed │ Check that field order_id has physical type DECIMAL(18,0) │ order_id │         │
│  ...   │                                                           │          │         │
╰────────┴───────────────────────────────────────────────────────────┴──────────┴─────────╯
🟢 Data contract is valid. Ran 6 checks. Took 1.4 seconds.
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

Run `datacontract test datacontract.yaml` again: every violation is listed as an error, and the command exits with code `1` — ready for [CI/CD and scheduled runs](../scheduling/index.md) so you catch drift before your consumers do.

## Metadata checks

Instead of the data, you can check what Exasol records about it. The system views, such as `EXA_ALL_OBJECTS` and `EXA_ALL_TABLES`, can be read from any schema, so the server keeps its own `schema` and its schemas name the views; every check works on them as on a table. `EXA_ALL_OBJECTS` records when each table was created and last written to:

```yaml
servers:
  - server: catalog
    type: exasol
    host: exasol.acme.com
    port: 8563
    schema: SALES  # not SYS: Exasol cannot read the views' columns from there
schema:
  - name: EXA_ALL_OBJECTS
    quality:
      - type: sql
        description: Every table in the SALES schema was written to in the last day
        query: |
          SELECT COUNT(*) FROM EXA_ALL_OBJECTS
          WHERE ROOT_NAME = 'SALES' AND OBJECT_TYPE = 'TABLE' AND LAST_COMMIT < ADD_DAYS(CURRENT_TIMESTAMP, -1)
        mustBe: 0
    properties:
      - name: OBJECT_NAME
        logicalType: string
        required: true
        logicalTypeOptions:
          pattern: "^[A-Z_0-9]+$"
      - name: CREATED
        logicalType: timestamp
        required: true
      - name: LAST_COMMIT
        logicalType: timestamp
```

## Reference

All authentication options (including TLS) and the data type handling: **[Exasol Reference](../reference/exasol.md)**.

## Troubleshooting

- **`Could not connect to Exasol: [SSL: CERTIFICATE_VERIFY_FAILED]`** — the cluster uses a certificate the system CA store does not know; pin it with `DATACONTRACT_EXASOL_FINGERPRINT`, see [TLS](../reference/exasol.md#tls).
- **`Connection exception - schema ... not found`** — the `schema` in the `servers` block must exist, and a mixed-case schema created with quotes must be spelled exactly (`"Sales"` is not found by `sales`).
