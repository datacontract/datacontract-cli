---
sidebar_position: 8
title: "Edit your contract"
description: "Author and edit data contracts visually with the bundled Data Contract Editor web UI."
---

# Edit your contract

The [Data Contract Editor](https://github.com/datacontract/datacontract-editor) is a web-based visual editor for ODCS data contracts. It is hosted at [editor.datacontract.com](https://editor.datacontract.com), and the CLI can launch it locally against a file on your machine.

## Edit a local file

```bash
datacontract edit odcs.yaml
```

This starts a local web server and opens the Data Contract Editor for the given file in your browser. The editor is bundled with the CLI, so **no internet access is required**. Saving in the editor writes directly back to the local file.

Key behaviors:

- If the file does not exist, you are asked whether to initialize a new data contract.
- If a **URL** is given, you are asked whether to download a local copy, which is then edited.
- The server also acts as the editor's **test runner**: clicking "Run test" in the editor executes the data contract tests locally against the servers defined in the contract. Credentials for the data sources must be provided as environment variables — see [Testing](./testing.md).

## Requirements

The `edit` command requires the `api` extra:

```bash
pip install 'datacontract-cli[api]'
```

The editor assets (JS/CSS) are bundled with the CLI and work offline by default. You can change where they are loaded from:

- `--editor-version` — load a specific version of the `datacontract-editor` npm package from the CDN, e.g. `0.1.9` or `latest`.
- `--editor-assets-url` — load assets from a self-hosted editor build. Takes precedence over `--editor-version`.

## Options

| Option | Default | Description |
|---|---|---|
| `--port` | `4243` | Bind the local server to this port. |
| `--host` | `127.0.0.1` | Bind to this host. For Docker, set it to `0.0.0.0`. |
| `--editor-version` | bundled | Version of the `datacontract-editor` npm package to load from the CDN. |
| `--editor-assets-url` | — | Base URL to load editor assets from (e.g. a self-hosted build). |
| `--open` / `--no-open` | `--open` | Open the editor in the default browser. |
| `--debug` / `--no-debug` | `--no-debug` | Enable debug logging. |

## Example

```bash
datacontract edit datacontract.yaml
```

See the [`edit` command reference](./commands/edit.md) for the full signature.
