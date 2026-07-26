---
sidebar_position: 16
title: "Oracle"
description: "Create a data contract from your Oracle tables and test the actual data against it."
---

# <img className="page-icon" src="/img/icons/oracle.svg" alt="" /> Oracle

Test data in Oracle Database.

## 1. Install

```bash
uv tool install --python python3.11 --upgrade 'datacontract-cli[oracle]'
```

See [Installation](../installation.md) for pip, pipx, and Docker.

## 2. Set credentials

Create a `.env` file in your working directory (or export the variables):

```bash
# .env
DATACONTRACT_ORACLE_USERNAME=system
DATACONTRACT_ORACLE_PASSWORD=mysecretpassword
```

## 3. Create a contract from your tables

Get the DDL of a table (e.g. `SELECT DBMS_METADATA.GET_DDL('TABLE', 'ORDERS') FROM dual;` in SQL*Plus or SQL Developer), save it to a file, and import it:

```bash
datacontract import sql --source orders.sql --dialect oracle --output datacontract.yaml
```

The SQL import can't know your connection details, so it writes a `servers` block with placeholder values. Open `datacontract.yaml` and fill in your server:

```yaml
servers:
  - server: oracle
    type: oracle
    host: localhost
    port: 1521
    service_name: ORCL
    schema: ADMIN
```

## 4. Test the actual data

```bash
datacontract test datacontract.yaml
```

```
🟢 data contract is valid. Run 24 checks. Took 3.4 seconds.
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

Run `datacontract test datacontract.yaml` again: every violation is listed as an error, and the command exits with code `1` — ready for [CI/CD scheduling](../testing.md#scheduling-and-cicd) so you catch drift before your consumers do.

## Reference

All authentication options and the data type mappings: **[Oracle Reference](../reference/oracle.md)**.

## Troubleshooting

- **`ORA-12514: TNS:listener does not currently know of service`** — `service_name` in the `servers` block doesn't match the database service; check with `lsnrctl status` or your DBA.
- **`DPY-3010: connections to this database server version are not supported`** — older Oracle versions need thick mode: install the Oracle Instant Client and set `DATACONTRACT_ORACLE_CLIENT_DIR`.
- **`ORA-00942: table or view does not exist`** — the `schema` in the `servers` block must be the owning schema (in uppercase), and the user needs `SELECT` on the table.
