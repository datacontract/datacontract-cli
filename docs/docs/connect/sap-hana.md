---
sidebar_position: 19
title: "SAP HANA"
description: "Test data in an SAP HANA database (HANA Cloud or on-premise)."
---

# SAP HANA

:::info[Required extra]
This connection requires the `sap-hana` extra. See [Installation](../installation.md).
:::

Test data in SAP HANA (HANA Cloud or on-premise).

SAP HANA has no native ibis or DuckDB backend, so the Data Contract CLI reads
each model's table over SAP's `hdbcli` driver and materializes it into DuckDB,
where the checks run. The full table is read into memory, so this suits the
dataset sizes typical of contract tests.

## Server

```yaml
servers:
  - server: sap-hana
    type: sap-hana
    host: my-instance.hanacloud.ondemand.com
    port: 443        # HANA Cloud: 443. On-premise: 3<instance>13, e.g. 39013
    schema: MYSCHEMA
```

| Field | Description |
|---|---|
| `host` | HANA host name or IP address |
| `port` | SQL port. HANA Cloud uses `443`; on-premise single-container uses `3<instance>13` (e.g. `39013`) |
| `schema` | Schema containing the tables to test |

## Environment variables

| Variable | Example | Description |
|---|---|---|
| `DATACONTRACT_SAP_HANA_USERNAME` | `SYSTEM` | Username (required) |
| `DATACONTRACT_SAP_HANA_PASSWORD` | `mysecretpassword` | Password (required) |
| `DATACONTRACT_SAP_HANA_ENCRYPT` | `true` | Use TLS. Defaults to `true` (required for HANA Cloud). Set `false` for on-premise without TLS |
| `DATACONTRACT_SAP_HANA_VALIDATE_CERT` | `true` | Validate the server TLS certificate. Defaults to `true`. Set `false` for self-signed certificates |
