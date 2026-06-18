---
sidebar_position: 2
title: "edit"
description: "Edit a data contract in the Data Contract Editor (web UI)."
---

# `datacontract edit`

Edit a data contract file in the [Data Contract Editor](../editor.md) (web UI). Starts a local web server that opens the editor for the given file; saving writes back to the local file. Requires the `api` extra.

```bash
datacontract edit [LOCATION]
```

| Argument | Default | Description |
|---|---|---|
| `LOCATION` | `datacontract.yaml` | Path of the data contract YAML to edit. If it does not exist, you are asked whether to initialize a new one. If a URL is given, you are asked whether to download a local copy. |

| Option | Default | Description |
|---|---|---|
| `--port` | `4243` | Bind the server to this port. |
| `--host` | `127.0.0.1` | Bind to this host (use `0.0.0.0` for Docker). |
| `--editor-version` | bundled | Version of the `datacontract-editor` npm package to load from the CDN. |
| `--editor-assets-url` | — | Base URL for editor assets (takes precedence over `--editor-version`). |
| `--open` / `--no-open` | `--open` | Open the editor in the default browser. |
| `--debug` / `--no-debug` | `--no-debug` | Enable debug logging. |

```bash
datacontract edit datacontract.yaml
```

See the [Data Contract Editor](../editor.md) guide for details.
