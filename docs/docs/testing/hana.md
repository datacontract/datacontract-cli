---
sidebar_position: 19
title: "SAP HANA"
description: "Test the actual data in SAP HANA Cloud and SAP Datasphere against your data contract."
---

# <img className="page-icon" src="/img/icons/database.svg" alt="" /> SAP HANA

Test data in SAP HANA Cloud and in the Open SQL schemas of SAP Datasphere.

## 1. Install

```bash
uv tool install --python python3.11 --upgrade 'datacontract-cli[hana]'
```

See [Installation](../installation.md) for pip, pipx, and Docker.

:::note
`hana` is not part of `datacontract-cli[all]`. It needs `hdbcli`, the SAP HANA Client, which SAP
distributes under its own license (the SAP Developer License), so you have to opt into it
explicitly and accept that license.
:::

## 2. Authenticate

Create a `.env` file in your working directory (or export the variables):

```bash
# .env
DATACONTRACT_HANA_USERNAME=MY_USER
DATACONTRACT_HANA_PASSWORD=mysecretpassword
```

| Environment variable                            | Default | Description                                               |
|-------------------------------------------------|---------|-----------------------------------------------------------|
| `DATACONTRACT_HANA_USERNAME`                    |         | Database user (required)                                  |
| `DATACONTRACT_HANA_PASSWORD`                    |         | Password (required)                                       |
| `DATACONTRACT_HANA_ENCRYPT`                     | `true`  | Use TLS. Keep it on for HANA Cloud and Datasphere.        |
| `DATACONTRACT_HANA_SSL_VALIDATE_CERTIFICATE`    | `true`  | Validate the server certificate                           |
| `DATACONTRACT_HANA_SSL_HOSTNAME_IN_CERTIFICATE` | `*`     | Expected host name in the certificate                     |

## 3. Describe the server in the contract

The `hana` server type was added in ODCS v3.2.0, so the contract has to declare
`apiVersion: v3.2.0`. There is no `datacontract import hana` yet: write the schema by hand, or
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
    type: hana
    host: abcd1234-1234-5678-90ab-cdef12345678.hana.prod-eu10.hanacloud.ondemand.com
    port: 443
    schema: SALES
schema:
  - name: orders
    physicalName: ORDERS
    properties:
      - name: order_id
        physicalName: ORDER_ID
        logicalType: string
        physicalType: NVARCHAR
        primaryKey: true
      - name: order_total
        physicalName: ORDER_TOTAL
        logicalType: number
        physicalType: DECIMAL
```

`schema` is the HANA schema the objects live in, and is required. For SAP Datasphere, use the Open
SQL schema you exposed the views in, and its host and port from the database user's connection
details.

## 4. Test the actual data

```bash
datacontract test datacontract.yaml
```

```
Testing datacontract.yaml
Server: production (type=hana, host=..., port=443, schema=SALES)
╭────────┬─────────────────────────────────────────────────┬─────────────────┬─────────╮
│ Result │ Check                                           │ Field           │ Details │
├────────┼─────────────────────────────────────────────────┼─────────────────┼─────────┤
│ passed │ Check that field ORDER_ID is present            │ ORDERS.ORDER_ID │         │
│ passed │ Check that field ORDER_ID has no missing values │ ORDERS.ORDER_ID │         │
│  ...   │                                                 │                 │         │
╰────────┴─────────────────────────────────────────────────┴─────────────────┴─────────╯
🟢 data contract is valid. Run 12 checks. Took 1.4 seconds.
```

The engine reads the declared types from `SYS.TABLE_COLUMNS` and `SYS.VIEW_COLUMNS`, and runs every
other check as SQL against the objects themselves.

## 5. Let it catch a violation

Add a quality rule to a schema in `datacontract.yaml`:

```yaml
schema:
  - name: orders
    # ...
    quality:
      - type: sql
        description: No order has a negative total
        query: SELECT COUNT(*) FROM {model} WHERE ORDER_TOTAL < 0
        mustBe: 0
```

Run `datacontract test datacontract.yaml` again: every violation is listed as an error, and the
command exits with code `1`, ready for [CI/CD and scheduled runs](../scheduling/index.md).

## SAP Datasphere

Objects in an Open SQL schema are mostly views, and a view carries no primary key or unique
constraint in the catalog. `primaryKey` and `unique` are therefore validated against the data
(`COUNT(*)` over the duplicated keys) rather than against constraint metadata, so they report
actual duplicates even where nothing declares the key.

## Notes and limitations

- `datacontract test --filter` / `--filters` restrict the rows the checks read, and
  `--dimension`, `--quality-id`, `--tag`, `--checks`, `--dry-run` and `--metadata-only` work as
  they do for the other engines.
- Quality rules of `type: custom` with `engine: soda` are not executed and report a warning. Write
  them as `type: sql` instead.
- `--include-failed-samples` collects no rows for HANA.

## Troubleshooting

- **`Install the extra datacontract-cli[hana]`** — `hdbcli` is missing, see step 1.
- **`Required environment variable DATACONTRACT_HANA_USERNAME is not set`** — the credentials come
  from the environment, never from the contract.
- **`Model SALES.ORDERS does not exist`** — the object names are case-sensitive as stored in the
  catalog, which is upper case unless it was created quoted. Use `physicalName` for the name in the
  database and keep `name` as the business name.
