import importlib.resources as resources
import io
import json
import logging
from collections import Counter
from copy import copy
from decimal import Decimal
from typing import Any, Optional

import openpyxl
import requests
from open_data_contract_standard.model import (
    DataQuality,
    OpenDataContractStandard,
    SchemaObject,
    SchemaProperty,
    Team,
)
from openpyxl.cell.cell import Cell
from openpyxl.utils import range_boundaries
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.workbook.workbook import Workbook
from openpyxl.worksheet.worksheet import Worksheet

from datacontract.export.exporter import Exporter
from datacontract.model.workbook import (
    CUSTOM_PROPERTIES_GROUP,
    SERVER_FIELDS,
    Element,
    InlineRoundTrip,
    is_scalar,
    iter_elements,
    server_field_name,
)

logger = logging.getLogger(__name__)

TEMPLATE_VERSION = 2  # the layout this exporter writes; older custom templates get one aggregated warning


class ExcelExporter(Exporter):
    """Excel exporter that uses the official ODCS template"""

    def __init__(self, export_format):
        super().__init__(export_format)

    def export(self, data_contract, schema_name, server, sql_server_type, export_args) -> bytes:
        template = export_args.get("template") if export_args else None
        return export_to_excel_bytes(data_contract, template)


class Export:
    """State of one export: the workbook, where rich custom properties go, and what the template cannot hold."""

    def __init__(self, workbook: Workbook, odcs: OpenDataContractStandard):
        self.workbook = workbook
        self.odcs = odcs
        self.elements = {id(e.obj): e for e in iter_elements(odcs)}
        self.round_trip = InlineRoundTrip(
            prop.value for e in self.elements.values() for prop in (getattr(e.obj, "customProperties", None) or [])
        )
        self.custom_property_rows: list[tuple[Element, Any]] = []
        self.authoritative_definition_rows: list[tuple[Element, Any]] = []
        self.unsupported = Counter()
        self.unaddressable: set[int] = set()

    def element(self, obj) -> Element:
        return self.elements.get(id(obj)) or Element("?", None, obj, "element", "is not addressable")

    def inline_custom_properties(self, obj, inline: bool = True) -> list[tuple[str, Any]]:
        """The (property, value) pairs written inline next to the element; the rest go to the Custom Properties sheet."""
        pairs = []
        for prop in getattr(obj, "customProperties", None) or []:
            if not prop.property:
                continue
            simple = (
                inline
                and not (prop.id or prop.description or prop.vendor)
                and prop.value is not None
                and self.round_trip.survives(prop.value)
            )
            if simple:
                pairs.append((prop.property, prop.value))
            else:
                self.custom_property_rows.append((self.element(obj), prop))
        return pairs

    def sheet_authoritative_definitions(self, obj, skip=0):
        for definition in (getattr(obj, "authoritativeDefinitions", None) or [])[skip:]:
            self.authoritative_definition_rows.append((self.element(obj), definition))

    def warn_unaddressable(self, element: Element, what: str) -> bool:
        """True (and a warning) when the element cannot be referenced from a child sheet."""
        if element.ref is not None:
            return False
        if id(element.obj) not in self.unaddressable:
            self.unaddressable.add(id(element.obj))
            logger.warning(
                f"Cannot reference {element.label} in the workbook: it {element.unaddressable_reason}; "
                f"its {what} were dropped. Give it an id."
            )
        return True


def export_to_excel_bytes(odcs: OpenDataContractStandard, template_path: Optional[str] = None) -> bytes:
    """Export ODCS to Excel using the official template (or a custom one) and return the workbook bytes."""
    if template_path:
        workbook = create_workbook_from_template(template_path)
    else:
        workbook = create_workbook_from_bundled_template()

    try:
        export = Export(workbook, odcs)
        fill_fundamentals(export)
        fill_schema(export)
        fill_relationships(export)
        fill_quality(export)
        fill_support(export)
        fill_team(export)
        fill_roles(export)
        fill_sla_properties(export)
        fill_servers(export)
        fill_pricing(export)
        fill_enum(export)
        fill_synonyms(export)
        fill_context_sheets(export)
        # last: the row fillers above decide what ends up here
        fill_custom_properties(export)
        fill_authoritative_definitions(export)
        warn_unsupported(export)

        workbook.active = workbook["Fundamentals"]
        try:
            workbook.calculation.calcMode = "auto"
        except (AttributeError, ValueError):
            pass

        output = io.BytesIO()
        workbook.save(output)
        return output.getvalue()
    finally:
        workbook.close()


def create_workbook_from_bundled_template() -> Workbook:
    """Load the official ODCS Excel template that ships with the CLI"""
    template = resources.files("datacontract").joinpath("templates", "excel", "odcs-template.xlsx")
    try:
        return openpyxl.load_workbook(io.BytesIO(template.read_bytes()))
    except Exception as e:
        logger.error(f"Failed to load the bundled Excel template: {e}")
        raise RuntimeError(f"Failed to load Excel template: {e}")


def create_workbook_from_template(template_path: str) -> Workbook:
    """Load Excel template from file path or URL"""
    try:
        template_path_str = str(template_path)
        if template_path_str.startswith(("http://", "https://")):
            logger.info(f"Downloading template from: {template_path_str}")
            response = requests.get(template_path_str, timeout=30)
            response.raise_for_status()
            return openpyxl.load_workbook(io.BytesIO(response.content))
        logger.info(f"Loading template from local file: {template_path_str}")
        return openpyxl.load_workbook(template_path_str)
    except Exception as e:
        logger.error(f"Failed to load Excel template from {template_path}: {e}")
        raise RuntimeError(f"Failed to load Excel template: {e}")


def warn_unsupported(export: Export):
    if not export.unsupported:
        return
    version = find_cell_by_name(export.workbook, "templateVersion")
    version = int(version.value) if version is not None and version.value is not None else 1
    dropped = ", ".join(f"{feature} ({count})" for feature, count in export.unsupported.items())
    logger.warning(
        f"Custom template (templateVersion {version}) cannot hold: {dropped}. "
        f"Upgrade to templateVersion {TEMPLATE_VERSION} to keep them."
    )


# --- Fundamentals, pricing ------------------------------------------------------------------------


def fill_fundamentals(export: Export):
    workbook, odcs = export.workbook, export.odcs
    set_cell_value_by_name(workbook, "apiVersion", odcs.apiVersion)
    set_cell_value_by_name(workbook, "kind", odcs.kind)
    set_cell_value_by_name(workbook, "id", odcs.id)
    set_cell_value_by_name(workbook, "name", odcs.name)
    set_cell_value_by_name(workbook, "version", odcs.version)
    set_cell_value_by_name(workbook, "status", odcs.status)
    set_cell_value_by_name(workbook, "domain", odcs.domain)
    set_cell_value_by_name(workbook, "dataProduct", odcs.dataProduct)
    set_cell_value_by_name(workbook, "tenant", odcs.tenant)

    owner_value = None
    for prop in odcs.customProperties or []:
        if prop.property == "owner":
            owner_value = prop.value
            break
    set_cell_value_by_name(workbook, "owner", owner_value)

    set_cell_value_by_name(workbook, "slaDefaultElement", odcs.slaDefaultElement)

    if odcs.description:
        set_cell_value_by_name(workbook, "description.purpose", odcs.description.purpose)
        set_cell_value_by_name(workbook, "description.limitations", odcs.description.limitations)
        set_cell_value_by_name(workbook, "description.usage", odcs.description.usage)

    if odcs.tags:
        set_cell_value_by_name(workbook, "tags", ",".join(odcs.tags))

    instructions = context_instructions(odcs.context)
    if instructions and not set_optional_cell(export, "context.instructions", instructions):
        export.unsupported["context instructions"] += 1


def context_instructions(context) -> Optional[str]:
    if context is None:
        return None
    return context if isinstance(context, str) else context.instructions


def fill_pricing(export: Export):
    if export.odcs.price:
        set_cell_value_by_name(export.workbook, "price.priceAmount", export.odcs.price.priceAmount)
        set_cell_value_by_name(export.workbook, "price.priceCurrency", export.odcs.price.priceCurrency)
        set_cell_value_by_name(export.workbook, "price.priceUnit", export.odcs.price.priceUnit)


# --- Schema sheets --------------------------------------------------------------------------------


def fill_schema(export: Export):
    """Fill schema information by cloning the template sheet once per schema"""
    workbook = export.workbook
    schema_template_sheet = workbook["Schema <table_name>"]

    if not export.odcs.schema_:
        workbook.remove(schema_template_sheet)
        return

    new_sheets = []
    for schema in export.odcs.schema_:
        new_sheet = workbook.copy_worksheet(schema_template_sheet)
        new_sheet.title = f"Schema {schema.name}"
        copy_sheet_names(workbook, schema_template_sheet, new_sheet)
        workbook.move_sheet(new_sheet, offset=workbook.index(schema_template_sheet) - workbook.index(new_sheet))
        new_sheets.append((new_sheet, schema))

    workbook.remove(schema_template_sheet)

    for new_sheet, schema in new_sheets:
        fill_single_schema(export, new_sheet, schema)


def copy_sheet_names(workbook: Workbook, template_sheet: Worksheet, new_sheet: Worksheet):
    """Copy worksheet-scoped named ranges from template sheet to new sheet"""
    for name_str in template_sheet.defined_names:
        try:
            original_ref = template_sheet.defined_names[name_str].attr_text
            new_ref = original_ref.replace(f"'{template_sheet.title}'", quote_sheet_title(new_sheet.title))
            new_sheet.defined_names.add(DefinedName(name_str, attr_text=new_ref))
        except Exception as e:
            logger.warning(f"Failed to copy worksheet-scoped named range {name_str}: {e}")


def quote_sheet_title(title: str) -> str:
    return "'" + title.replace("'", "''") + "'"


def fill_single_schema(export: Export, sheet: Worksheet, schema: SchemaObject):
    set_cell_value_by_name_in_sheet(sheet, "schema.name", schema.name)
    set_cell_value_by_name_in_sheet(sheet, "schema.physicalType", schema.physicalType or "table")
    set_cell_value_by_name_in_sheet(sheet, "schema.description", schema.description)
    set_cell_value_by_name_in_sheet(sheet, "schema.businessName", schema.businessName)
    set_cell_value_by_name_in_sheet(sheet, "schema.physicalName", schema.physicalName)
    set_cell_value_by_name_in_sheet(sheet, "schema.dataGranularityDescription", schema.dataGranularityDescription)
    if schema.tags:
        set_cell_value_by_name_in_sheet(sheet, "schema.tags", ",".join(schema.tags))

    for name, value, feature in (
        ("schema.id", schema.id, "ids"),
        ("schema.deprecated", schema.deprecated, "deprecated flags"),
        ("schema.context.instructions", context_instructions(schema.context), "context instructions"),
    ):
        if value is None:
            continue
        cell = find_cell_by_name_in_sheet(sheet, name)
        if cell is None:
            export.unsupported[feature] += 1
        else:
            set_cell_value_direct(cell, value)

    export.sheet_authoritative_definitions(schema)
    export.inline_custom_properties(schema, inline=False)  # the schema block has no inline columns

    if schema.properties:
        header_row = properties_header_row(sheet)
        header_map = header_columns(sheet, header_row)
        row_index = header_row + 1
        for prop in schema.properties:
            row_index = fill_property_row(export, sheet, header_row, header_map, row_index, "", prop)


def properties_header_row(sheet: Worksheet) -> int:
    ref = name_to_ref_in_sheet(sheet, "schema.properties")
    return parse_range_safely(ref) if ref else 13


LOGICAL_TYPE_OPTION_HEADERS = {
    "Minimum Length": "minLength",
    "Maximum Length": "maxLength",
    "Pattern": "pattern",
    "Format": "format",
    "Exclusive Maximum": "exclusiveMaximum",
    "Exclusive Minimum": "exclusiveMinimum",
    "Minimum": "minimum",
    "Maximum": "maximum",
    "Multiple Of": "multipleOf",
    "Minimum Items": "minItems",
    "Maximum Items": "maxItems",
    "Unique Items": "uniqueItems",
    "Maximum Properties": "maxProperties",
    "Minimum Properties": "minProperties",
    "Required Properties": "required",
    "Dimensions": "dimensions",
    "Element Type": "elementType",
    "Distance Metric": "distanceMetric",
    "Normalized": "normalized",
    "Embedding Model": "embeddingModel",
    "Embedding Model Version": "embeddingModelVersion",
}


def fill_property_row(
    export: Export,
    sheet: Worksheet,
    header_row: int,
    header_map: dict,
    row_index: int,
    prefix: str,
    prop: SchemaProperty,
    is_items: bool = False,
) -> int:
    property_name = prefix if is_items else (f"{prefix}.{prop.name}" if prefix else prop.name)

    def set_by_header(header_name: str, value: Any, feature: Optional[str] = None):
        col_idx = header_map.get(header_name.lower())
        if col_idx is not None:
            set_cell_value_direct(sheet.cell(row=row_index, column=col_idx + 1), value)
        elif feature and value is not None:
            export.unsupported[feature] += 1

    set_by_header("Property", property_name)
    set_by_header("Business Name", prop.businessName)
    set_by_header("Logical Type", prop.logicalType)
    set_by_header("Physical Type", prop.physicalType)
    set_by_header("Physical Name", prop.physicalName)
    set_by_header("Description", prop.description)
    set_by_header("Required", prop.required)
    set_by_header("Unique", prop.unique)
    set_by_header("Primary Key", prop.primaryKey)
    set_by_header("Primary Key Position", prop.primaryKeyPosition)
    set_by_header("Partitioned", prop.partitioned)
    set_by_header("Partition Key Position", prop.partitionKeyPosition)
    set_by_header("Classification", prop.classification)
    set_by_header("Tags", ",".join(prop.tags) if prop.tags else "")
    set_by_header("Example(s)", ",".join(map(str, prop.examples)) if prop.examples else "")
    set_by_header("Encrypted Name", prop.encryptedName)
    set_by_header("Transform Sources", ",".join(prop.transformSourceObjects) if prop.transformSourceObjects else "")
    set_by_header("Transform Logic", prop.transformLogic)
    set_by_header("Transform Description", prop.transformDescription)
    set_by_header("Critical Data Element Status", prop.criticalDataElement)
    for header, option in LOGICAL_TYPE_OPTION_HEADERS.items():
        value = (prop.logicalTypeOptions or {}).get(option)
        set_by_header(header, ",".join(value) if isinstance(value, list) else value)
    set_by_header("Semantic Type", prop.semanticType, "semantic types")
    set_by_header("Deprecated", prop.deprecated, "deprecated flags")
    set_by_header("ID", prop.id, "ids")

    # the first plain definition keeps its inline home, the rest go to the Authoritative Definitions sheet
    definitions = prop.authoritativeDefinitions or []
    inline = 0
    if definitions and "authoritative definition url" in header_map:
        first = definitions[0]
        if not (first.id or first.description):
            set_by_header("Authoritative Definition URL", first.url)
            set_by_header("Authoritative Definition Type", first.type)
            inline = 1
    export.sheet_authoritative_definitions(prop, skip=inline)

    write_inline_custom_properties(export, sheet, header_row, row_index, prop)

    next_row_index = row_index + 1
    for nested in prop.properties or []:
        next_row_index = fill_property_row(export, sheet, header_row, header_map, next_row_index, property_name, nested)
    if prop.items:
        # array items are the row "<parent>.items"; their own name is not written
        next_row_index = fill_property_row(
            export, sheet, header_row, header_map, next_row_index, f"{property_name}.items", prop.items, is_items=True
        )
    return next_row_index


# --- Row sheets ----------------------------------------------------------------------------------


def row_sheet(export: Export, sheet_title: str, range_name: str, fallback_header_row=None, header=None):
    """(sheet, header row index) of a row sheet, or None when the template has no such sheet.

    `header` names a column the header row must contain; a range starting on the first data row is stepped up one row.
    """
    workbook = export.workbook
    if sheet_title not in workbook.sheetnames:
        return None
    sheet = workbook[sheet_title]
    ref = name_to_ref(workbook, range_name) or name_to_ref_in_sheet(sheet, range_name)
    if ref:
        header_row = parse_range_safely(ref)
        if header and header not in header_columns(sheet, header_row) and header_row > 1:
            header_row -= 1
        return sheet, header_row
    if fallback_header_row:
        return sheet, fallback_header_row
    return None


def write_row(export: Export, sheet: Worksheet, header_row: int, row_index: int, values: dict, obj=None):
    """Write one row: `values` maps lower-cased header names to values; `obj` supplies the id and inline pairs."""
    headers = get_headers_from_header_row(sheet, header_row)
    for cell_index, header_name in headers.items():
        key = header_name.lower().strip()
        if key in values:
            set_cell_value(sheet, row_index, cell_index, values[key])
    if obj is not None:
        if getattr(obj, "id", None) is not None:
            if "id" in {h.lower().strip() for h in headers.values()}:
                set_cell_value(
                    sheet, row_index, [i for i, h in headers.items() if h.lower().strip() == "id"][0], obj.id
                )
            else:
                export.unsupported["ids"] += 1
        write_inline_custom_properties(export, sheet, header_row, row_index, obj)
        export.sheet_authoritative_definitions(obj)


def fill_quality(export: Export):
    found = row_sheet(export, "Quality", "quality")
    if not found:
        return
    sheet, header_row = found
    row_index = header_row + 1
    for schema in export.odcs.schema_ or []:
        for quality in schema.quality or []:
            write_row(export, sheet, header_row, row_index, quality_values(schema.name, None, quality), quality)
            row_index += 1
        row_index = fill_properties_quality(export, sheet, header_row, schema.name, schema.properties or [], row_index)


def fill_properties_quality(export, sheet, header_row, schema_name, properties, row_index) -> int:
    for path, prop in walk_properties(properties):
        for quality in prop.quality or []:
            write_row(export, sheet, header_row, row_index, quality_values(schema_name, path, quality), quality)
            row_index += 1
    return row_index


def walk_properties(properties, prefix=""):
    """(dotted path, property) of every property, depth first; array items are "<parent>.items"."""
    for prop in properties or []:
        if not prop.name:
            continue
        path = f"{prefix}.{prop.name}" if prefix else prop.name
        yield path, prop
        yield from walk_properties(prop.properties, path)
        if prop.items:
            yield f"{path}.items", prop.items
            yield from walk_properties(prop.items.properties, f"{path}.items")


def quality_values(schema_name: str, property_name: Optional[str], quality: DataQuality) -> dict:
    return {
        "schema": schema_name,
        "property": property_name,
        "quality type": quality.type,
        "description": quality.description,
        "rule (library)": quality.rule,
        "query (sql)": quality.query,
        "threshold operator": get_threshold_operator(quality),
        "threshold value": get_threshold_value(quality),
        "quality engine (custom)": quality.engine,
        "implementation (custom)": quality.implementation,
        "severity": quality.severity,
        "scheduler": quality.scheduler,
        "schedule": quality.schedule,
    }


THRESHOLD_OPERATORS = (
    "mustBe",
    "mustNotBe",
    "mustBeGreaterThan",
    "mustBeGreaterThanOrEqualTo",
    "mustBeGreaterOrEqualTo",
    "mustBeLessThan",
    "mustBeLessThanOrEqualTo",
    "mustBeLessOrEqualTo",
    "mustBeBetween",
    "mustNotBeBetween",
)


def get_threshold_operator(quality: DataQuality) -> Optional[str]:
    for operator in THRESHOLD_OPERATORS:
        if getattr(quality, operator, None) is not None:
            return operator
    return None


def get_threshold_value(quality: DataQuality) -> Optional[str]:
    operator = get_threshold_operator(quality)
    if operator is None:
        return None
    value = getattr(quality, operator)
    if operator in ("mustBeBetween", "mustNotBeBetween"):
        return f"[{value[0]}, {value[1]}]" if len(value) >= 2 else None
    return str(value)


def fill_relationships(export: Export):
    found = row_sheet(export, "Relationships", "relationships")
    rows = []
    for schema in export.odcs.schema_ or []:
        for rel in schema.relationships or []:
            rows.append(({"level": "schema", "type": rel.type, "from": join(rel.from_), "to": join(rel.to)}, rel))
        for path, prop in walk_properties(schema.properties):
            for rel in prop.relationships or []:
                values = {"level": "property", "type": rel.type, "from": f"{schema.name}.{path}", "to": join(rel.to)}
                rows.append((values, rel))
    if not rows:
        return
    if not found:
        export.unsupported["relationships"] += len(rows)
        return
    sheet, header_row = found
    for offset, (values, rel) in enumerate(rows):
        write_row(export, sheet, header_row, header_row + 1 + offset, values, rel)


def join(value) -> Optional[str]:
    if value is None:
        return None
    return ", ".join(value) if isinstance(value, list) else str(value)


def fill_support(export: Export):
    found = row_sheet(export, "Support", "support")
    if not found:
        return
    sheet, header_row = found
    for offset, support in enumerate(export.odcs.support or []):
        values = {
            "channel": support.channel,
            "channel url": support.url,
            "description": support.description,
            "tool": support.tool,
            "scope": support.scope,
            "invitation url": support.invitationUrl,
        }
        write_row(export, sheet, header_row, header_row + 1 + offset, values, support)


def fill_team(export: Export):
    team = export.odcs.team
    members = team.members if isinstance(team, Team) else team
    if isinstance(team, Team):
        for name, value in (
            ("team.name", team.name),
            ("team.description", team.description),
            ("team.tags", ",".join(team.tags) if team.tags else None),
            ("team.id", team.id),
        ):
            if value is not None and not set_optional_cell(export, name, value):
                export.unsupported["team details"] += 1
        # the team block has no inline pairs: every custom property goes to the sheet
        export.custom_property_rows += [(export.element(team), prop) for prop in team.customProperties or []]
        export.sheet_authoritative_definitions(team)
    found = row_sheet(export, "Team", "team")
    if not found:
        return
    sheet, header_row = found
    for offset, member in enumerate(members or []):
        values = {
            "username": member.username,
            "name": member.name,
            "description": member.description,
            "role": member.role,
            "date in": member.dateIn,
            "date out": member.dateOut,
            "replaced by username": member.replacedByUsername,
        }
        write_row(export, sheet, header_row, header_row + 1 + offset, values, member)


def fill_roles(export: Export):
    found = row_sheet(export, "Roles", "roles", fallback_header_row=4)
    if not found:
        return
    sheet, header_row = found
    for offset, role in enumerate(export.odcs.roles or []):
        values = {
            "role": role.role,
            "description": role.description,
            "access": role.access,
            "1st level approvers": role.firstLevelApprovers,
            "2nd level approvers": role.secondLevelApprovers,
        }
        write_row(export, sheet, header_row, header_row + 1 + offset, values, role)


def fill_sla_properties(export: Export):
    found = row_sheet(export, "SLA", "slaProperties", fallback_header_row=6)
    if not found:
        return
    sheet, header_row = found
    for offset, sla in enumerate(export.odcs.slaProperties or []):
        values = {
            "property": sla.property,
            "value": sla.value,
            "extended value": sla.valueExt,
            "unit": sla.unit,
            "element": sla.element,
            "driver": sla.driver,
        }
        write_row(export, sheet, header_row, header_row + 1 + offset, values, sla)


# --- Servers -------------------------------------------------------------------------------------


def fill_servers(export: Export):
    workbook = export.workbook
    if "Servers" not in workbook.sheetnames or not export.odcs.servers:
        return
    sheet = workbook["Servers"]
    for index, server in enumerate(export.odcs.servers):
        set_cell_value_by_column_index(sheet, "servers.server", index, server.server)
        set_cell_value_by_column_index(sheet, "servers.description", index, server.description)
        set_cell_value_by_column_index(sheet, "servers.environment", index, server.environment)
        set_cell_value_by_column_index(sheet, "servers.type", index, server.type)
        for field in SERVER_FIELDS:
            value = getattr(server, "schema_" if field == "schema" else field)
            if value is None:
                continue
            name = server_field_name(workbook, server.type, field)
            if name:
                set_cell_value_by_column_index(sheet, name, index, value)
            else:
                export.unsupported[f"server field {field}"] += 1
        if server.id is not None:
            if find_cell_by_name(workbook, "servers.id"):
                set_cell_value_by_column_index(sheet, "servers.id", index, server.id)
            else:
                export.unsupported["ids"] += 1
        write_server_custom_properties(export, sheet, index, server)


def write_server_custom_properties(export: Export, sheet: Worksheet, index: int, server):
    """Servers are columns: property names go in column B below the group label, values in the server's column."""
    label_row = next(
        (
            row
            for row in range(1, sheet.max_row + 1)
            if cell_text(sheet.cell(row=row, column=1)) == CUSTOM_PROPERTIES_GROUP
        ),
        None,
    )
    pairs = export.inline_custom_properties(server, inline=label_row is not None)
    if not pairs:
        return
    first = find_cell_by_name(sheet.parent, "servers.server")
    column = first.column + index if first else 3 + index
    rows = list(range(label_row + 1, sheet.max_row + 1))
    for key, value in pairs:
        row = next((r for r in rows if cell_text(sheet.cell(row=r, column=2)) == key), None)
        if row is None:
            row = next((r for r in rows if cell_text(sheet.cell(row=r, column=2)) is None), None)
        if row is None:
            row = rows[-1] + 1
            rows.append(row)
            for col in range(2, 27):
                sheet.cell(row=row, column=col)._style = copy(sheet.cell(row=row - 1, column=col)._style)
        sheet.cell(row=row, column=2).value = key
        set_cell_value_direct(sheet.cell(row=row, column=column), value)


# --- Child sheets: enum, synonyms, context, custom properties, authoritative definitions -------------


def fill_enum(export: Export):
    rows = []
    for schema in export.odcs.schema_ or []:
        for path, prop in walk_properties(schema.properties):
            for enum_value in prop.enum or []:
                values = {
                    "schema": schema.name,
                    "property": path,
                    "value": enum_value.value,
                    "label": enum_value.label,
                    "description": enum_value.description,
                    "tags": ",".join(enum_value.tags) if enum_value.tags else None,
                }
                rows.append((values, enum_value))
    if not rows:
        return
    found = row_sheet(export, "Enums", "enum")
    if not found:
        export.unsupported["enum values"] += len(rows)
        return
    sheet, header_row = found
    for offset, (values, enum_value) in enumerate(rows):
        write_row(export, sheet, header_row, header_row + 1 + offset, values, enum_value)


def fill_synonyms(export: Export):
    rows = []
    for schema in export.odcs.schema_ or []:
        for synonym in schema.synonyms or []:
            rows.append((synonym_values(schema.name, None, synonym), synonym))
        for path, prop in walk_properties(schema.properties):
            for synonym in prop.synonyms or []:
                rows.append((synonym_values(schema.name, path, synonym), synonym))
    if not rows:
        return
    found = row_sheet(export, "Synonyms", "synonyms")
    if not found:
        export.unsupported["synonyms"] += len(rows)
        return
    sheet, header_row = found
    for offset, (values, synonym) in enumerate(rows):
        write_row(export, sheet, header_row, header_row + 1 + offset, values, synonym)


def synonym_values(schema_name, property_path, synonym) -> dict:
    return {
        "schema": schema_name,
        "property": property_path,
        "synonym": synonym.synonym,
        "description": synonym.description,
        "locale": synonym.locale,
        "source": synonym.source,
        "status": synonym.status,
    }


def fill_context_sheets(export: Export):
    statements, constraints = [], []
    contexts = [("Contract", None, export.odcs.context)]
    contexts += [("Schema", schema.name, schema.context) for schema in export.odcs.schema_ or []]
    for level, schema_name, context in contexts:
        if context is None or isinstance(context, str):
            continue
        for statement in context.verifiedStatements or []:
            values = {
                "level": level,
                "schema": schema_name,
                "question": statement.question,
                "answer": statement.answer,
                "tags": ",".join(statement.tags) if statement.tags else None,
            }
            statements.append((values, statement))
        for constraint in context.constraints or []:
            values = {
                "level": level,
                "schema": schema_name,
                "constraint": constraint.constraint,
                "tags": ",".join(constraint.tags) if constraint.tags else None,
            }
            constraints.append((values, constraint))
    for title, range_name, feature, rows in (
        ("Verified Statements", "verifiedStatements", "verified statements", statements),
        ("Constraints", "constraints", "constraints", constraints),
    ):
        if not rows:
            continue
        found = row_sheet(export, title, range_name)
        if not found:
            export.unsupported[feature] += len(rows)
            continue
        sheet, header_row = found
        for offset, (values, obj) in enumerate(rows):
            write_row(export, sheet, header_row, header_row + 1 + offset, values, obj)


def fill_custom_properties(export: Export):
    """The Custom Properties sheet: rich properties of every element, plus the contract's own"""
    rows = [(export.element(export.odcs), prop) for prop in export.odcs.customProperties or []]
    if export.odcs.description:
        rows += [
            (export.element(export.odcs.description), prop) for prop in export.odcs.description.customProperties or []
        ]
    rows += export.custom_property_rows
    found = row_sheet(export, "Custom Properties", "CustomProperties", header="property")
    if not found:
        export.unsupported["custom properties"] += len(rows)
        return
    sheet, header_row = found
    headers = {h.lower().strip() for h in get_headers_from_header_row(sheet, header_row).values()}
    row_index = header_row + 1
    if "element type" not in headers:
        # pre-3.2 layout: a flat Property / Value table for the contract root only
        for element, prop in rows:
            if element.kind != "Contract" or prop.property == "owner":
                export.unsupported["custom properties"] += 1
                continue
            set_cell_value(sheet, row_index, 0, prop.property)
            set_cell_value(sheet, row_index, 1, prop.value if is_scalar(prop.value) else json.dumps(prop.value))
            row_index += 1
        return
    for element, prop in rows:
        if element.kind == "Contract" and prop.property == "owner" and not (prop.id or prop.description or prop.vendor):
            continue  # the Owner cell on Fundamentals holds it
        if export.warn_unaddressable(element, "custom properties"):
            continue
        value, value_type = typed_value(export, prop.value)
        values = {
            "element type": element.kind,
            "element": element.ref,
            "property": prop.property,
            "value": value,
            "type": value_type,
            "description": prop.description,
            "vendor": prop.vendor,
            "id": prop.id,
        }
        write_row(export, sheet, header_row, row_index, values)
        row_index += 1


def typed_value(export: Export, value: Any) -> tuple[Any, Optional[str]]:
    """The cell value and `Type` that reproduce `value` on import."""
    if not is_scalar(value):
        return json.dumps(value), "JSON"
    if export.round_trip.survives(value):
        return value, None
    if isinstance(value, str):
        return value, "Text"
    return json.dumps(value), "JSON"


def fill_authoritative_definitions(export: Export):
    rows = list(export.authoritative_definition_rows)
    for definition in export.odcs.authoritativeDefinitions or []:
        rows.append((export.element(export.odcs), definition))
    if export.odcs.description:
        for definition in export.odcs.description.authoritativeDefinitions or []:
            rows.append((export.element(export.odcs.description), definition))
    if not rows:
        return
    found = row_sheet(export, "Authoritative Definitions", "authoritativeDefinitions")
    if not found:
        export.unsupported["authoritative definitions"] += len(rows)
        return
    sheet, header_row = found
    row_index = header_row + 1
    for element, definition in rows:
        if export.warn_unaddressable(element, "authoritative definitions"):
            continue
        values = {
            "element type": element.kind,
            "element": element.ref,
            "url": definition.url,
            "type": definition.type,
            "description": definition.description,
            "id": definition.id,
        }
        write_row(export, sheet, header_row, row_index, values)
        row_index += 1


# --- Inline custom property columns ------------------------------------------------------------


def custom_property_columns(sheet: Worksheet, header_row: int) -> Optional[tuple[int, list[Optional[str]]]]:
    """(first column, header names) of the columns under the "Custom Properties (add as needed)" group header, else None."""
    group_row = header_row - 1
    start = next((c.column for c in sheet[group_row] if cell_text(c) == CUSTOM_PROPERTIES_GROUP), None)
    if start is None:
        return None
    last = max([c.column for c in sheet[header_row] if c.value is not None] + [start + 2])
    return start, [cell_text(sheet.cell(row=header_row, column=col)) for col in range(start, last + 1)]


def write_inline_custom_properties(export: Export, sheet: Worksheet, header_row: int, row_index: int, obj):
    """One column per property name under the group header; a new name takes the next empty column or a new one."""
    region = custom_property_columns(sheet, header_row)
    pairs = export.inline_custom_properties(obj, inline=region is not None)
    if not pairs:
        return
    start, names = region
    for key, value in pairs:
        if key in names:
            offset = names.index(key)
        elif None in names:
            offset = names.index(None)
            names[offset] = key
            sheet.cell(row=header_row, column=start + offset).value = key
        else:
            offset = len(names)
            names.append(key)
            column = start + offset
            sheet.cell(row=header_row, column=column, value=key)._style = copy(
                sheet.cell(row=header_row, column=column - 1)._style
            )
            for row in range(header_row + 1, header_row + 18):
                sheet.cell(row=row, column=column)._style = copy(sheet.cell(row=row, column=column - 1)._style)
            for merged in list(sheet.merged_cells.ranges):
                if merged.min_row == header_row - 1 and merged.min_col == start:
                    sheet.merged_cells.remove(merged)
                    sheet.merge_cells(
                        start_row=merged.min_row, start_column=start, end_row=merged.min_row, end_column=column
                    )
        set_cell_value_direct(sheet.cell(row=row_index, column=start + offset), value)


def cell_text(cell: Cell) -> Optional[str]:
    return str(cell.value).strip() or None if cell.value is not None else None


# --- Cell helpers --------------------------------------------------------------------------------


def find_cell_by_name(workbook: Workbook, name: str) -> Optional[Cell]:
    """Find a cell by its (workbook-scoped) named range"""
    try:
        ref = name_to_ref(workbook, name)
        if not ref:
            return None
        return find_cell_by_ref(workbook, ref)
    except Exception:
        return None


def find_cell_by_name_in_sheet(sheet: Worksheet, name: str) -> Optional[Cell]:
    """Find a cell by its worksheet-scoped named range"""
    try:
        if name in sheet.defined_names:
            for sheet_title, coordinate in sheet.defined_names[name].destinations:
                if sheet_title == sheet.title:
                    return sheet[coordinate]
    except Exception:
        return None
    return None


def find_cell_by_ref(workbook: Workbook, cell_ref: str) -> Optional[Cell]:
    try:
        sheet_name, _, coord = cell_ref.rpartition("!")
        sheet = workbook[sheet_name.strip("'").replace("''", "'")] if sheet_name else workbook.active
        min_col, min_row, _, _ = range_boundaries(coord.replace("$", ""))
        return sheet.cell(row=min_row, column=min_col)
    except Exception:
        return None


def name_to_ref(workbook: Workbook, name: str) -> Optional[str]:
    defined_name = workbook.defined_names.get(name)
    return defined_name.attr_text if defined_name else None


def name_to_ref_in_sheet(sheet: Worksheet, name: str) -> Optional[str]:
    defined_name = sheet.defined_names.get(name)
    return defined_name.attr_text if defined_name else None


def set_optional_cell(export: Export, name: str, value: Any) -> bool:
    """Set a named cell that only newer templates have; False when the template lacks it."""
    cell = find_cell_by_name(export.workbook, name)
    if cell is None:
        return False
    set_cell_value_direct(cell, value)
    return True


def set_cell_value_by_name(workbook: Workbook, cell_name: str, value: Any):
    cell = find_cell_by_name(workbook, cell_name)
    if cell:
        set_cell_value_direct(cell, value)
    else:
        logger.warning(f"Cell with name {cell_name} not found in workbook")


def set_cell_value_by_name_in_sheet(sheet: Worksheet, cell_name: str, value: Any):
    cell = find_cell_by_name_in_sheet(sheet, cell_name)
    if cell:
        set_cell_value_direct(cell, value)
    else:
        logger.warning(f"Cell with name {cell_name} not found in sheet {sheet.title}")


def set_cell_value_by_column_index(sheet: Worksheet, name: str, column_index: int, value: Any):
    """Set cell value by column offset from a named cell (servers are laid out horizontally)"""
    first_cell = find_cell_by_name(sheet.parent, name)
    if first_cell:
        set_cell_value_direct(sheet.cell(row=first_cell.row, column=first_cell.column + column_index), value)


def set_cell_value_direct(cell: Cell, value: Any):
    if value is None:
        cell.value = None
    elif isinstance(value, (bool, int, float)):
        cell.value = value
    elif isinstance(value, Decimal):
        cell.value = int(value) if value == value.to_integral_value() else float(value)
    else:
        cell.value = str(value)


def set_cell_value(sheet: Worksheet, row_index: int, cell_index: int, value: Any):
    set_cell_value_direct(sheet.cell(row=row_index, column=cell_index + 1), value)


def parse_range_safely(ref: str) -> int:
    """The first row of a range reference such as Quality!$A$4:$AZ$300"""
    _, _, coord = ref.rpartition("!")
    _, min_row, _, _ = range_boundaries(coord.replace("$", ""))
    return min_row


def get_headers_from_header_row(sheet: Worksheet, header_row_index: int) -> dict:
    """Headers of a row as dict mapping 0-based cell index -> header name"""
    return {cell.column - 1: str(cell.value).strip() for cell in sheet[header_row_index] if cell.value}


def header_columns(sheet: Worksheet, header_row_index: int) -> dict:
    """Lower-cased header name -> 0-based column index (the first occurrence wins)"""
    columns = {}
    for index, header in get_headers_from_header_row(sheet, header_row_index).items():
        columns.setdefault(header.lower(), index)
    return columns
