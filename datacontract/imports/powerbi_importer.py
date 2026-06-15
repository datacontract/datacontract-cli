from __future__ import annotations

import json
import logging
import re
import zipfile
from pathlib import Path
from typing import Any

from open_data_contract_standard.model import (
    CustomProperty,
    OpenDataContractStandard,
    Relationship,
    SchemaObject,
    SchemaProperty,
)

from datacontract.imports.importer import Importer
from datacontract.imports.odcs_helper import create_odcs, create_property, create_schema_object, create_server
from datacontract.model.exceptions import DataContractException

# ---------------------------------------------------------------------------
# Power BI data type → (ODCS logical type, optional format)
# ---------------------------------------------------------------------------
_PBI_TYPE_TO_ODCS: dict[str, tuple[str, str | None]] = {
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


def _map_pbi_type(data_type: str | None) -> tuple[str, str | None]:
    """Map a Power BI data type string to ``(logicalType, format)``."""
    if data_type is None:
        return ("string", None)
    return _PBI_TYPE_TO_ODCS.get(data_type.lower(), ("string", None))


def _normalize(name: str) -> str:
    """Turn a Power BI name into a valid ODCS identifier token.

    Examples:
        "Sales"        → "Sales"
        "Account Owner" → "Account_Owner"
        "Sales MoM %"   → "Sales_MoM_percent"
    """
    normalized = re.sub(r"[^A-Za-z0-9_]", "_", name.replace("%", "percent"))
    if normalized[:1].isdigit():
        normalized = "_" + normalized
    return normalized


# ---------------------------------------------------------------------------
# Importer class
# ---------------------------------------------------------------------------


class PowerBiImporter(Importer):
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
            reason=(f"Unsupported file extension '{suffix}'. Supported formats: .pbit, .bim, .json"),
            engine="datacontract",
        )

    return _build_odcs(bim, model_name=path.stem)


# ---------------------------------------------------------------------------
# BIM loaders
# ---------------------------------------------------------------------------


def _load_bim_from_pbit(pbit_path: Path) -> dict[str, Any]:
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


def _load_bim_from_json(bim_path: Path) -> dict[str, Any]:
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


def _build_odcs(bim: dict[str, Any], model_name: str) -> OpenDataContractStandard:
    # Some BIM files wrap everything under a top-level "model" key; others don't.
    model = bim.get("model", bim)

    odcs = create_odcs(
        id=model_name.lower().replace(" ", "-"),
        name=model_name,
    )

    odcs.servers = [
        create_server(
            name="powerbi",
            server_type="custom",
            path=model_name,
        )
    ]

    tables = model.get("tables", [])
    bim_relationships = model.get("relationships", [])

    schema_objects: list[SchemaObject] = []
    # original BIM table name → SchemaObject (for relationship wiring)
    table_name_to_obj: dict[str, SchemaObject] = {}

    for table in tables:
        schema_obj = _map_table(table)
        if schema_obj is not None:
            t_name = table.get("name", "")
            schema_objects.append(schema_obj)
            table_name_to_obj[t_name] = schema_obj

    _apply_bim_relationships(bim_relationships, table_name_to_obj)

    if not schema_objects:
        logging.warning("Power BI import produced an empty contract: No tables were found in the semantic model.")

    schema_objects.sort(key=lambda s: s.name.lower())
    odcs.schema_ = schema_objects
    return odcs


# ---------------------------------------------------------------------------
# Table → SchemaObject
# ---------------------------------------------------------------------------


def _map_table(table: dict[str, Any]) -> SchemaObject | None:
    name = table.get("name", "")
    if not name:
        return None
    if name.startswith("LocalDateTable_"):
        return None
    if name.startswith("DateTableTemplate_"):
        return None

    description = table.get("description") or None
    is_hidden = table.get("isHidden", False)
    physical_type = _table_physical_type(table)
    tags = ["hidden"] if is_hidden else None

    properties: list[SchemaProperty] = []

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
        name=_normalize(name),
        physical_type=physical_type,
        description=description,
        business_name=name,
        tags=tags,
        properties=properties if properties else None,
    )

    return schema_obj


def _table_physical_type(table: dict[str, Any]) -> str:
    partitions = table.get("partitions", [])
    if not partitions:
        return "table"
    source_type = partitions[0].get("source", {}).get("type", "")
    return "calculated table" if source_type == "calculated" else "table"


# ---------------------------------------------------------------------------
# Column → SchemaProperty
# ---------------------------------------------------------------------------


def _map_column(col: dict[str, Any]) -> SchemaProperty | None:
    name = col.get("name", "")
    if not name:
        return None

    data_type = col.get("dataType", "string")
    column_type = col.get("columnType", "data")
    is_calculated = column_type == "calculated"

    logical_type, fmt = _map_pbi_type(data_type)
    physical_type = "calculated column" if is_calculated else data_type
    is_nullable = col.get("isNullable", True)
    description = col.get("description") or None

    custom_props: dict[str, Any] = {}

    if col.get("formatString"):
        custom_props["formatString"] = col["formatString"]
    if col.get("displayFolder"):
        custom_props["displayFolder"] = col["displayFolder"]
    if col.get("summarizeBy") and col["summarizeBy"] not in ("none", "default", None):
        custom_props["summarizeBy"] = col["summarizeBy"]
    if col.get("isHidden"):
        custom_props["isHidden"] = True

    expression = col.get("expression")
    if isinstance(expression, list):
        expression = "".join(expression)

    property = create_property(
        name=_normalize(name),
        logical_type=logical_type,
        physical_type=physical_type,
        description=description,
        required=True if not is_nullable else None,
        format=fmt,
        custom_properties=custom_props if custom_props else None,
    )

    property.businessName = name
    property.transformLogic = expression.strip() if expression else None

    return property


# ---------------------------------------------------------------------------
# Measure → SchemaProperty
# ---------------------------------------------------------------------------


def _map_measure(measure: dict[str, Any]) -> SchemaProperty | None:
    name = measure.get("name", "")
    if not name:
        return None

    description = measure.get("description") or None
    expression = measure.get("expression", "")
    # Power BI sometimes stores multi-line DAX as a list of strings
    if isinstance(expression, list):
        expression = "\n".join(expression)

    custom_props: dict[str, Any] = {}
    if measure.get("isHidden"):
        custom_props["isHidden"] = True
    if measure.get("displayFolder"):
        custom_props["displayFolder"] = measure["displayFolder"]

    logical_type = _infer_measure_type(measure.get("formatString", ""), expression)

    property = create_property(
        name=_normalize(name),
        logical_type=logical_type,
        physical_type="measure",
        description=description,
        custom_properties=custom_props if custom_props else None,
    )
    property.businessName = name
    property.transformLogic = expression.strip() if expression else None

    return property


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


def _map_hierarchy(hierarchy: dict[str, Any]) -> SchemaProperty | None:
    name = hierarchy.get("name", "")
    if not name:
        return None

    description = hierarchy.get("description") or None
    levels = sorted(hierarchy.get("levels", []), key=lambda lv: lv.get("ordinal", 0))

    level_props = []
    for lv in levels:
        if not lv.get("name"):
            continue
        level_prop = create_property(
            name=_normalize(lv.get("name")),
            logical_type="string",
            physical_type="hierarchy level",
            custom_properties={"columnRef": _normalize(lv["column"])} if lv.get("column") else None,
        )
        level_prop.businessName = lv.get("name")
        level_props.append(level_prop)

    hierarchy_prop = create_property(
        name=_normalize(name),
        logical_type="object",
        physical_type="hierarchy",
        description=description,
        properties=level_props if level_props else None,
    )
    hierarchy_prop.businessName = name
    return hierarchy_prop


# ---------------------------------------------------------------------------
# Relationships
# ---------------------------------------------------------------------------


def _apply_bim_relationships(
    bim_relationships: list[dict[str, str]],
    table_name_to_obj: dict[str, SchemaObject],
) -> None:
    """Attach BIM relationships as ODCS Relationship objects on the 'from' SchemaObject.

    ``from`` and ``to`` are ``table.column`` references built from the normalized
    (identifier-safe) names, so each matches the ``name`` of its target.
    The relationship is placed on the *from* side (many side) of the join.
    """
    for rel in bim_relationships:
        from_table = rel.get("fromTable", "")
        from_col_name = rel.get("fromColumn", "")
        to_table = rel.get("toTable", "")
        to_col_name = rel.get("toColumn", "")

        from_obj = table_name_to_obj.get(from_table)
        to_obj = table_name_to_obj.get(to_table)
        if from_obj is None or to_obj is None:
            continue

        from_card = rel.get("fromCardinality", "many")
        to_card = rel.get("toCardinality", "one")
        is_active = rel.get("isActive", True)

        custom_props = [CustomProperty(property="cardinality", value=f"{from_card}-to-{to_card}")]
        if not is_active:
            custom_props.append(CustomProperty(property="active", value=False))

        odcs_rel = Relationship(
            type="foreignKey",
            **{"from": f"{_normalize(from_table)}.{_normalize(from_col_name)}"},
            to=f"{_normalize(to_table)}.{_normalize(to_col_name)}",
            customProperties=custom_props,
        )

        if from_obj.relationships is None:
            from_obj.relationships = []
        from_obj.relationships.append(odcs_rel)
