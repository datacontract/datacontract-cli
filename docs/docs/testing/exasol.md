---
sidebar_position: 10
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

| Environment variable                       | Default | Description                                                    |
|--------------------------------------------|---------|----------------------------------------------------------------|
| `DATACONTRACT_EXASOL_USERNAME`             |         | Database user (required)                                       |
| `DATACONTRACT_EXASOL_PASSWORD`             |         | Password (required)                                            |
| `DATACONTRACT_EXASOL_FINGERPRINT`          |         | SHA-256 fingerprint of the server certificate, see [TLS](#tls) |
| `DATACONTRACT_EXASOL_VALIDATE_CERTIFICATE` | `true`  | Set to `false` to skip the certificate check, see [TLS](#tls)  |
| `DATACONTRACT_EXASOL_HOST`                 |         | Overrides `host` in the `servers` block                        |
| `DATACONTRACT_EXASOL_PORT`                 | `8563`  | Overrides `port` in the `servers` block                        |
| `DATACONTRACT_EXASOL_SCHEMA`               |         | Overrides `schema` in the `servers` block                      |

## 3. Describe the server in the contract

The `exasol` server type was added in ODCS v3.2.0, so the contract has to declare
`apiVersion: v3.2.0`.

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

## 4. Test actual data

```bash
datacontract test datacontract.yaml
```

```
Testing datacontract.yaml
Server: production (type=exasol, host=exasol.acme.com, port=8563, schema=sales)
╭────────┬─────────────────────────────────────────────────┬─────────────────┬─────────╮
│ Result │ Check                                           │ Field           │ Details │
├────────┼─────────────────────────────────────────────────┼─────────────────┼─────────┤
│ passed │ Check that field 'order_id' is present          │ orders.order_id │         │
│ passed │ Check that field order_id has no missing values │ orders.order_id │         │
│  ...   │                                                 │                 │         │
╰────────┴─────────────────────────────────────────────────┴─────────────────┴─────────╯
🟢 data contract is valid. Run 12 checks. Took 1.4 seconds.
```

## 5. Add quality checks

Add a quality rule to a schema in `datacontract.yaml`:

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

Run `datacontract test datacontract.yaml` again: every violation is listed as an error, and the
command exits with code `1` — ready for [CI/CD and scheduled runs](../scheduling/index.md) so you
catch drift before your consumers do.

## TLS

Connections are always encrypted, and the server certificate is verified against the system CA
store. For a cluster with a self-signed certificate, pin it by its SHA-256 fingerprint instead —
the value Exasol clients accept after the host in a connection string:

```bash
# .env
DATACONTRACT_EXASOL_FINGERPRINT=135A1D2DCE102DE866F58267521F4232153545A075DC85F8F7596F57E588A181
```

`DATACONTRACT_EXASOL_VALIDATE_CERTIFICATE=false` skips the verification altogether. A CA bundle of
your own goes into the `WEBSOCKET_CLIENT_CA_BUNDLE` environment variable.

## Troubleshooting

- **`Could not connect to Exasol: [SSL: CERTIFICATE_VERIFY_FAILED]`** — the cluster uses a
  certificate the system CA store does not know; pin it with `DATACONTRACT_EXASOL_FINGERPRINT`, see [TLS](#tls).
- **`Connection exception - schema ... not found`** — the `schema` in the `servers` block must exist, and a mixed-case
  schema created with quotes must be spelled exactly (`"Sales"` is not found by `sales`).
