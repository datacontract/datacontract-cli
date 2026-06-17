---
sidebar_position: 16
title: "Extending the CLI"
description: "Register custom exporters and importers to add new output and input formats to the Data Contract CLI."
---

# Extending the CLI

The CLI uses factory patterns for export and import, so you can register your own **custom exporter** (a new output format) or **custom importer** (a new input format) and use them through the same `DataContract` API.

:::note
For producing a custom text output from a Jinja template, you usually don't need code — use the built-in [`export custom`](./exports/custom.md) exporter. Register a custom exporter class (below) when you need full programmatic control.
:::

## Custom exporter

Implement `Exporter.export(...)` and register the class with the exporter factory. The `data_contract` argument is an `OpenDataContractStandard` (ODCS) instance, so you read `data_contract.name`, `data_contract.version`, `data_contract.schema_`, etc.

```python
from datacontract.data_contract import DataContract
from datacontract.export.exporter import Exporter
from datacontract.export.exporter_factory import exporter_factory


class MyExporter(Exporter):
    def export(self, data_contract, schema_name, server, sql_server_type, export_args) -> str:
        lines = [f"# {data_contract.name} v{data_contract.version}"]
        for schema in data_contract.schema_ or []:
            columns = ", ".join(p.name for p in (schema.properties or []))
            lines.append(f"{schema.name}: {columns}")
        return "\n".join(lines)


# Register the exporter under a new format name
exporter_factory.register_exporter("my_format", MyExporter)

# Use it like any built-in format
data_contract = DataContract(data_contract_file="datacontract.yaml")
print(data_contract.export("my_format"))
```

The `export()` method receives:

| Argument | Description |
|---|---|
| `data_contract` | The contract as an `OpenDataContractStandard` object. |
| `schema_name` | The selected schema, or `"all"`. |
| `server` | The selected server name (or `None`). |
| `sql_server_type` | The SQL dialect (`"auto"` by default). |
| `export_args` | A dict of any extra keyword arguments passed to `export(...)`. |

## Custom importer

Implement `Importer.import_source(...)` to build and return an `OpenDataContractStandard`, then register it with the importer factory.

```python
import json
from open_data_contract_standard.model import (
    OpenDataContractStandard,
    SchemaObject,
    SchemaProperty,
)
from datacontract.data_contract import DataContract
from datacontract.imports.importer import Importer
from datacontract.imports.importer_factory import importer_factory


class MyImporter(Importer):
    def import_source(self, source, import_args) -> OpenDataContractStandard:
        data = json.loads(source)
        return OpenDataContractStandard(
            apiVersion="v3.0.2",
            kind="DataContract",
            id=data["id"],
            name=data["title"],
            version=data["version"],
            description={"purpose": data.get("description")},
            schema=[
                SchemaObject(
                    name=model["name"],
                    properties=[
                        SchemaProperty(name=col["name"], logicalType=col.get("type"))
                        for col in model["columns"]
                    ],
                )
                for model in data.get("models", [])
            ],
        )


# Register the importer under a new format name
importer_factory.register_importer("my_format", MyImporter)

source = '{"id": "urn:my:contract", "title": "My Contract", "version": "1.0.0", "models": []}'
odcs = DataContract.import_from_source(format="my_format", source=source)

# import_from_source returns an ODCS object; wrap it to export or test
print(DataContract(data_contract=odcs).export("odcs"))
```

## Tips

- Register classes once at import time (e.g. in a small plugin module you import before using the CLI as a library).
- Custom formats are only available through the [Python library](./python-library.md), not the standalone `datacontract` command.
- See the built-in exporters/importers in the [source tree](https://github.com/datacontract/datacontract-cli/tree/main/datacontract) for complete, real-world implementations.
