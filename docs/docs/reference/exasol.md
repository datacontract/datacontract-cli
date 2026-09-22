---
sidebar_position: 8
title: "Exasol Reference"
sidebar_label: "Exasol"
description: "All Exasol authentication options and data type handling."
---

# <img className="page-icon" src="/img/icons/exasol.svg" alt="" /> Exasol Reference

Authentication options and data type handling for [Exasol connections](../testing/exasol.md).

## Server

```yaml
servers:
  - server: production
    type: exasol
    host: exasol.acme.com
    port: 8563
    schema: sales
```

`host` may be a cluster range (`n11..14.acme.com`). The `exasol` server type was added in ODCS v3.2.0, so the contract has to declare `apiVersion: v3.2.0`.

## Authentication

| Variable | Example | Description |
|---|---|---|
| `DATACONTRACT_EXASOL_USERNAME` | `sys` | Database user |
| `DATACONTRACT_EXASOL_PASSWORD` | `mysecretpassword` | Password |
| `DATACONTRACT_EXASOL_FINGERPRINT` | `135A1D2D...` | SHA-256 fingerprint of the server certificate, see [TLS](#tls) |
| `DATACONTRACT_EXASOL_VALIDATE_CERTIFICATE` | `false` | Set to `false` to skip the certificate check. Defaults to `true` |

`host`, `port`, and `schema` come from the contract's `servers` block, and can be overridden with `DATACONTRACT_EXASOL_HOST`, `DATACONTRACT_EXASOL_PORT`, and `DATACONTRACT_EXASOL_SCHEMA`. `port` defaults to `8563`.

### TLS

Connections are always encrypted, and the server certificate is verified against the system CA store. For a cluster with a self-signed certificate, pin it by its SHA-256 fingerprint instead — the value Exasol clients accept after the host in a connection string:

```bash
# .env
DATACONTRACT_EXASOL_FINGERPRINT=135A1D2DCE102DE866F58267521F4232153545A075DC85F8F7596F57E588A181
```

`DATACONTRACT_EXASOL_VALIDATE_CERTIFICATE=false` skips the verification altogether. A CA bundle of your own goes into the `WEBSOCKET_CLIENT_CA_BUNDLE` environment variable.