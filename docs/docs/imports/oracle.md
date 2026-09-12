---
sidebar_position: 19
title: "Import: Oracle"
description: "Create a data contract from an Oracle database."
---

# <img className="page-icon" src="/img/icons/oracle.svg" alt="" /> Import: Oracle

Creates a data contract from an Oracle database by reading `ALL_TAB_COLUMNS` — including column types with length and precision, nullability, and primary keys.

```bash
datacontract import oracle \
  --source localhost \
  --service-name XEPDB1 \
  --schema ADMIN \
  --output datacontract.yaml
```

`--source` is the host of your Oracle database and `--service-name` its service. Add `--port` if it doesn't listen on the default `1521`, and repeat `--table` to import only specific tables. Oracle stores identifiers in upper case, so `--schema` is upper-cased for you.

Types are reconstructed exactly as the test path reads them back. Oracle reports a `DATA_LENGTH` for *every* column, but it is only part of the declared type for character and raw types — so a `DATE` stays `DATE` rather than becoming `DATE(7)`.

The generated contract includes a ready-to-test `servers` block, so you can run `datacontract test datacontract.yaml` immediately afterwards — see the **[Oracle connection guide](../testing/oracle.md)** for the full 5-minute walkthrough and troubleshooting.

Credentials are the same ones `datacontract test` uses: `DATACONTRACT_ORACLE_USERNAME` and `DATACONTRACT_ORACLE_PASSWORD` — see the [Oracle Reference](../reference/oracle.md).

Only have a DDL script? Use [`datacontract import sql --dialect oracle`](./sql.md).

All options: **[`datacontract import oracle`](../commands/import/oracle.md)**.
