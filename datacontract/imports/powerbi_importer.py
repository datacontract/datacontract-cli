"""Power BI .pbit / .pbip / model.bim importer for the Data Contract CLI.

Extraction strategy (in priority order):
  1. ``.pbit`` — read the embedded ``DataModelSchema`` entry (UTF-16 LE BIM JSON).
  2. ``.bim`` or ``.json`` — read directly as a BIM JSON file (e.g. from pbi-tools
     or a Power BI Project / .pbip folder).
  3. If ``DataModelSchema`` is absent from the .pbit, a clear error is raised
     with instructions to re-save from an up-to-date Power BI Desktop or to
     extract the model using pbi-tools (https://pbi.tools).

What gets mapped to ODCS:
  - Tables          → SchemaObject  (physicalType: table | calculated table)
  - Columns         → SchemaProperty (logicalType via PBI type map)
  - Calculated cols → SchemaProperty (physicalType: calculated column, DAX in customProperties)
  - Measures        → SchemaProperty (physicalType: measure, DAX in customProperties)
  - Hierarchies     → SchemaProperty (logicalType: object, levels as nested properties)
  - Relationships   → customProperties on the source SchemaObject
  - Hidden tables   → included but tagged with "hidden"
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from open_data_contract_standard.model import (
    CustomProperty,
    OpenDataContractStandard,
    SchemaObject,
    SchemaProperty,
)

from datacontract.imports.importer import Importer
from datacontract.imports.odcs_helper import create_odcs, create_property, create_schema_object, create_server
from datacontract.model.exceptions import DataContractException

# ---------------------------------------------------------------------------
# Power BI data type → (ODCS logical type, optional format)
# ---------------------------------------------------------------------------
_PBI_TYPE_MAP: Dict[str, tuple[str, Optional[str]]] = {
    "string": ("string", None),
    "int64": ("integer", None),
    "double": ("number", None),
    "decimal": ("number", None),
    "boolean": ("boolean", None),
    "datetime": ("timestamp", None),
    "date": ("date", None),
    "time": ("time", None),
    "binary": ("string", "binary"),
    "duration": ("string", None),
    "unknown": ("string", None),
    "variant": ("object", None),
}


def _map_pbi_type(data_type: Optional[str]) -> tuple[str, Optional[str]]:
    """Map a Power BI data type string to ``(logicalType, format)``."""
    if data_type is None:
        return ("string", None)
    return _PBI_TYPE_MAP.get(data_type.lower(), ("string", None))


# ---------------------------------------------------------------------------
# Importer class
# ---------------------------------------------------------------------------


class PowerBIImporter(Importer):
    def import_source(self, source: str, import_args: dict) -> OpenDataContractStandard:
        if source is None:
            raise DataContractException(
                type="source",
                name="powerbi import source",
                reason=(
                    "Source file path is required for Power BI import. "
                    "Provide a path to a .pbit file, a .bim file, or a model.bim JSON file."
                ),
                engine="datacontract",
            )
        return import_powerbi_from_file(source_path=source)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def import_powerbi_from_file(source_path: str) -> OpenDataContractStandard:
    """Import a Power BI semantic model from a ``.pbit``, ``.bim``, or ``.json`` file."""
    path = Path(source_path)
    if not path.exists():
        raise DataContractException(
            type="import",
            name="powerbi import",
            reason=f"File not found: {source_path}",
            engine="datacontract",
        )

    suffix = path.suffix.lower()
    if suffix == ".pbit":
        bim = _load_bim_from_pbit(path)
    elif suffix in (".bim", ".json"):
        bim = _load_bim_from_json(path)
    else:
        raise DataContractException(
            type="import",
            name="powerbi import",
            reason=(f"Unsupported file extension '{suffix}'. Supported formats: .pbit, .bim, .json (model.bim)"),
            engine="datacontract",
        )

    return _build_odcs(bim, model_name=path.stem)


# ---------------------------------------------------------------------------
# BIM loaders
# ---------------------------------------------------------------------------


def _load_bim_from_pbit(pbit_path: Path) -> Dict[str, Any]:
    """Extract and parse the ``DataModelSchema`` JSON from a .pbit ZIP archive.

    Power BI Desktop embeds the tabular model as a UTF-16 LE JSON file called
    ``DataModelSchema`` inside the .pbit ZIP archive.  This entry has been
    present since mid-2021; older files may not include it.
    """
    _ENTRY_NAME = "DataModelSchema"
    try:
        with zipfile.ZipFile(pbit_path, "r") as zf:
            if _ENTRY_NAME not in zf.namelist():
                raise DataContractException(
                    type="import",
                    name="powerbi import",
                    reason=(
                        f"'DataModelSchema' was not found inside '{pbit_path.name}'. "
                        "This entry is present in Power BI Desktop files saved since mid-2021. "
                        "Try re-saving the file from an up-to-date Power BI Desktop, or export "
                        "the model as a .bim file using pbi-tools (https://pbi.tools) and "
                        "import that instead."
                    ),
                    engine="datacontract",
                )
            raw = zf.read(_ENTRY_NAME)
    except zipfile.BadZipFile as exc:
        raise DataContractException(
            type="import",
            name="powerbi import",
            reason=f"'{pbit_path.name}' is not a valid .pbit / ZIP file: {exc}",
            engine="datacontract",
            original_exception=exc,
        )

    # DataModelSchema is always UTF-16 LE, optionally with a BOM
    text = raw.decode("utf-16-le").lstrip("\ufeff")
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise DataContractException(
            type="import",
            name="powerbi import",
            reason=f"Failed to parse DataModelSchema JSON: {exc}",
            engine="datacontract",
            original_exception=exc,
        )


def _load_bim_from_json(bim_path: Path) -> Dict[str, Any]:
    """Load a ``model.bim`` / ``.json`` file as BIM JSON (UTF-8 with optional BOM)."""
    try:
        with open(bim_path, encoding="utf-8-sig") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        raise DataContractException(
            type="import",
            name="powerbi import",
            reason=f"Failed to read BIM file '{bim_path}': {exc}",
            engine="datacontract",
            original_exception=exc,
        )


# ---------------------------------------------------------------------------
# ODCS builder
# ---------------------------------------------------------------------------


def _build_odcs(bim: Dict[str, Any], model_name: str) -> OpenDataContractStandard:
    # Some BIM files wrap everything under a top-level "model" key; others don't.
    model = bim.get("model", bim)

    odcs = create_odcs(
        id=model_name.lower().replace(" ", "-"),
        name=model_name,
    )

    odcs.servers = [
        create_server(
            name="powerbi",
            server_type="powerbi",
            path=model_name,
        )
    ]

    schema_objects: List[SchemaObject] = []
    relationships = model.get("relationships", [])
    for table in model.get("tables", []):
        schema_obj = _map_table(table, relationships)
        if schema_obj is not None:
            schema_objects.append(schema_obj)

    schema_objects.sort(key=lambda s: s.name.lower())
    odcs.schema_ = schema_objects
    return odcs


# ---------------------------------------------------------------------------
# Table → SchemaObject
# ---------------------------------------------------------------------------


def _map_table(table: Dict[str, Any], relationships: List[Dict[str, Any]]) -> Optional[SchemaObject]:
    name = table.get("name", "")
    if not name:
        return None

    description = table.get("description") or None
    is_hidden = table.get("isHidden", False)
    physical_type = _table_physical_type(table)
    tags = ["hidden"] if is_hidden else None

    properties: List[SchemaProperty] = []

    # Columns — skip internal rowNumber columns added by the engine
    for col in table.get("columns", []):
        if col.get("columnType") == "rowNumber":
            continue
        prop = _map_column(col)
        if prop:
            properties.append(prop)

    # Measures
    for measure in table.get("measures", []):
        prop = _map_measure(measure)
        if prop:
            properties.append(prop)

    # Hierarchies
    for hierarchy in table.get("hierarchies", []):
        prop = _map_hierarchy(hierarchy)
        if prop:
            properties.append(prop)

    schema_obj = create_schema_object(
        name=name,
        physical_type=physical_type,
        description=description,
        tags=tags,
        properties=properties if properties else None,
    )

    # Relationships where this table is the "from" side go into customProperties
    table_rels = _get_table_relationships(name, relationships)
    if table_rels:
        schema_obj.customProperties = [
            CustomProperty(property=f"relationship_{i + 1}", value=rel) for i, rel in enumerate(table_rels)
        ]

    return schema_obj


def _table_physical_type(table: Dict[str, Any]) -> str:
    partitions = table.get("partitions", [])
    if not partitions:
        return "table"
    source_type = partitions[0].get("source", {}).get("type", "")
    return "calculated table" if source_type == "calculated" else "table"


# ---------------------------------------------------------------------------
# Column → SchemaProperty
# ---------------------------------------------------------------------------


def _map_column(col: Dict[str, Any]) -> Optional[SchemaProperty]:
    name = col.get("name", "")
    if not name:
        return None

    data_type = col.get("dataType", "string")
    logical_type, fmt = _map_pbi_type(data_type)
    is_nullable = col.get("isNullable", True)
    description = col.get("description") or None

    custom_props: Dict[str, Any] = {}

    column_type = col.get("columnType", "data")
    if column_type == "calculated":
        physical_type = "calculated column"
        expression = col.get("expression", "")
        if expression:
            custom_props["daxExpression"] = expression.strip()
    else:
        physical_type = "data column"

    if col.get("formatString"):
        custom_props["formatString"] = col["formatString"]
    if col.get("displayFolder"):
        custom_props["displayFolder"] = col["displayFolder"]
    if col.get("summarizeBy") and col["summarizeBy"] not in ("none", "default", None):
        custom_props["summarizeBy"] = col["summarizeBy"]
    if col.get("isHidden"):
        custom_props["isHidden"] = True

    return create_property(
        name=name,
        logical_type=logical_type,
        physical_type=physical_type,
        description=description,
        required=True if not is_nullable else None,
        format=fmt,
        custom_properties=custom_props if custom_props else None,
    )


# ---------------------------------------------------------------------------
# Measure → SchemaProperty
# ---------------------------------------------------------------------------


def _map_measure(measure: Dict[str, Any]) -> Optional[SchemaProperty]:
    name = measure.get("name", "")
    if not name:
        return None

    description = measure.get("description") or None
    expression = measure.get("expression", "")
    # Power BI sometimes stores multi-line DAX as a list of strings
    if isinstance(expression, list):
        expression = "\n".join(expression)

    custom_props: Dict[str, Any] = {}
    if expression:
        custom_props["daxExpression"] = expression.strip()
    if measure.get("formatString"):
        custom_props["formatString"] = measure["formatString"]
    if measure.get("displayFolder"):
        custom_props["displayFolder"] = measure["displayFolder"]
    if measure.get("isHidden"):
        custom_props["isHidden"] = True

    logical_type = _infer_measure_type(measure.get("formatString", ""), expression)

    return create_property(
        name=name,
        logical_type=logical_type,
        physical_type="measure",
        description=description,
        custom_properties=custom_props if custom_props else None,
    )


def _infer_measure_type(format_string: str, expression: str) -> str:
    """Best-effort inference of a measure's return type from its format string."""
    if not format_string:
        return "number"
    fs = format_string.lower()
    if any(k in fs for k in ["yyyy", "mmm", "ddd", "hh:mm"]):
        return "timestamp"
    if "true" in fs or "false" in fs:
        return "boolean"
    # Numeric format patterns: digits, comma separators, currency, percentage
    if any(c in fs for c in ["#", "0", "%", "$", "€", "£"]):
        return "number"
    return "number"


# ---------------------------------------------------------------------------
# Hierarchy → SchemaProperty
# ---------------------------------------------------------------------------


def _map_hierarchy(hierarchy: Dict[str, Any]) -> Optional[SchemaProperty]:
    name = hierarchy.get("name", "")
    if not name:
        return None

    description = hierarchy.get("description") or None
    levels = sorted(hierarchy.get("levels", []), key=lambda lv: lv.get("ordinal", 0))

    level_props = [
        create_property(
            name=lv["name"],
            logical_type="string",
            physical_type="hierarchy level",
            custom_properties={"columnRef": lv["column"]} if lv.get("column") else None,
        )
        for lv in levels
        if lv.get("name")
    ]

    return create_property(
        name=name,
        logical_type="object",
        physical_type="hierarchy",
        description=description,
        properties=level_props if level_props else None,
    )


# ---------------------------------------------------------------------------
# Relationships helper
# ---------------------------------------------------------------------------


def _get_table_relationships(table_name: str, relationships: List[Dict[str, Any]]) -> List[str]:
    """Return human-readable relationship strings where this table is the 'from' side."""
    result = []
    for rel in relationships:
        if rel.get("fromTable") != table_name:
            continue
        from_col = rel.get("fromColumn", "?")
        to_table = rel.get("toTable", "?")
        to_col = rel.get("toColumn", "?")
        from_card = rel.get("fromCardinality", "many")
        to_card = rel.get("toCardinality", "one")
        active = "" if rel.get("isActive", True) else " [inactive]"
        result.append(f"{table_name}[{from_col}] → {to_table}[{to_col}] ({from_card}-to-{to_card}){active}")
    return result
