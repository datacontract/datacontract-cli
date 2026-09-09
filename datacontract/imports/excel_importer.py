import json
import logging
import os
from typing import Any, Dict, List, Optional

import openpyxl
from open_data_contract_standard.model import (
    AuthoritativeDefinition,
    Constraint,
    Context,
    CustomProperty,
    DataQuality,
    Description,
    EnumValue,
    OpenDataContractStandard,
    Relationship,
    Role,
    SchemaObject,
    SchemaProperty,
    Server,
    ServiceLevelAgreementProperty,
    Support,
    Synonym,
    Team,
    TeamMember,
    VerifiedStatement,
)
from openpyxl.cell.cell import Cell
from openpyxl.utils import range_boundaries
from openpyxl.workbook.workbook import Workbook
from openpyxl.worksheet.worksheet import Worksheet

from datacontract.imports.importer import Importer
from datacontract.model.exceptions import DataContractException
from datacontract.model.workbook import (
    CUSTOM_PROPERTIES_GROUP,
    SERVER_FIELDS,
    element_index,
    resolve_cell_value,
    server_field_name,
)

logger = logging.getLogger(__name__)


class ExcelImporter(Importer):
    def import_source(
        self,
        source: str,
        import_args: dict,
    ) -> OpenDataContractStandard:
        return import_excel_as_odcs(source)


def import_excel_as_odcs(excel_file_path: str) -> OpenDataContractStandard:
    """Import an Excel file and convert it to an OpenDataContractStandard object"""
    if not os.path.exists(excel_file_path):
        raise FileNotFoundError(f"Excel file not found: {excel_file_path}")

    try:
        workbook = openpyxl.load_workbook(excel_file_path, data_only=True)
    except Exception as e:
        raise DataContractException(
            type="schema",
            name="Parse excel contract",
            reason=f"Failed to open Excel file: {excel_file_path}",
            engine="datacontract-cli",
            original_exception=e,
        )

    try:
        purpose = get_cell_value_by_name(workbook, "description.purpose")
        limitations = get_cell_value_by_name(workbook, "description.limitations")
        usage = get_cell_value_by_name(workbook, "description.usage")
        description = None
        if purpose or limitations or usage:
            description = Description(purpose=purpose, limitations=limitations, usage=usage)

        schemas = import_schemas(workbook)
        schemas = attach_quality_to_schemas(schemas, import_quality(workbook))
        attach_relationships(schemas, workbook)
        attach_enum_values(schemas, workbook)
        attach_synonyms(schemas, workbook)

        odcs = OpenDataContractStandard(
            apiVersion=get_cell_value_by_name(workbook, "apiVersion"),
            kind=get_cell_value_by_name(workbook, "kind"),
            id=get_cell_value_by_name(workbook, "id"),
            name=get_cell_value_by_name(workbook, "name"),
            version=get_cell_value_by_name(workbook, "version"),
            status=get_cell_value_by_name(workbook, "status"),
            domain=get_cell_value_by_name(workbook, "domain"),
            dataProduct=get_cell_value_by_name(workbook, "dataProduct"),
            tenant=get_cell_value_by_name(workbook, "tenant"),
            description=description,
            tags=split_list(get_cell_value_by_name(workbook, "tags")),
            schema=schemas,
            support=import_support(workbook),
            price=import_price(workbook),
            team=import_team(workbook),
            roles=import_roles(workbook),
            slaDefaultElement=get_cell_value_by_name(workbook, "slaDefaultElement"),
            slaProperties=import_sla_properties(workbook),
            servers=import_servers(workbook),
            customProperties=import_root_custom_properties(workbook),
            context=context_from(get_cell_value_by_name(workbook, "context.instructions"), None, None),
        )
        attach_context_statements(odcs, workbook)
        attach_custom_properties(odcs, workbook)
        attach_authoritative_definitions(odcs, workbook)
        return odcs
    except Exception as e:
        logger.error(f"Error importing Excel file: {str(e)}")
        raise DataContractException(
            type="schema",
            name="Parse excel contract",
            reason=f"Failed to parse Excel file: {excel_file_path}",
            engine="datacontract-cli",
            original_exception=e,
        )
    finally:
        workbook.close()


# --- Row sheets ----------------------------------------------------------------------------------


BLANK_ROW_LIMIT = 100  # stop scanning a sheet after this many consecutive empty rows


def last_row(sheet: Worksheet, first_row: int, columns) -> int:
    """The last row with a value in `columns`, giving up after BLANK_ROW_LIMIT consecutive empty rows.

    A named range is no upper bound: the export writes as many rows as the contract has, past the range's end.
    """
    last, blank = first_row - 1, 0
    for row in range(first_row, sheet.max_row + 1):
        if all(sheet.cell(row=row, column=column).value is None for column in columns):
            blank += 1
            if blank > BLANK_ROW_LIMIT:
                break
        else:
            last, blank = row, 0
    return last


class RowSheet:
    """A sheet with a header row and one element per row, located by its named range."""

    def __init__(self, sheet: Worksheet, header_row: int):
        self.sheet = sheet
        self.header_row = header_row
        self.columns: Dict[str, int] = {}
        for cell in sheet[header_row]:
            if cell.value is not None:
                self.columns.setdefault(str(cell.value).strip().lower(), cell.column)
        # the columns under "Custom Properties (add as needed)", each named after one property
        self.custom_columns: Dict[str, int] = {}
        start = next(
            (c.column for c in sheet[header_row - 1] if (cell_text(c.value) or "").startswith(CUSTOM_PROPERTIES_GROUP)),
            None,
        )
        if start is not None:
            for cell in sheet[header_row]:
                name = cell_text(cell.value)
                if cell.column >= start and name:
                    self.custom_columns.setdefault(name, cell.column)

    def rows(self):
        columns = set(self.columns.values()) | set(self.custom_columns.values())
        for row_index in range(self.header_row + 1, last_row(self.sheet, self.header_row + 1, columns) + 1):
            yield Row(self, row_index)


class Row:
    def __init__(self, row_sheet: RowSheet, row_index: int):
        self.row_sheet = row_sheet
        self.row_index = row_index

    def raw(self, header: str) -> Any:
        column = self.row_sheet.columns.get(header)
        return None if column is None else self.row_sheet.sheet.cell(row=self.row_index, column=column).value

    def text(self, header: str) -> Optional[str]:
        return cell_text(self.raw(header))

    def custom_properties(self) -> Optional[List[CustomProperty]]:
        sheet = self.row_sheet.sheet
        return inline_custom_properties(
            [
                (name, sheet.cell(row=self.row_index, column=col).value)
                for name, col in self.row_sheet.custom_columns.items()
            ]
        )


def open_row_sheet(workbook: Workbook, sheet_title: str, range_name: str, fallback_header_row=None, header=None):
    """The RowSheet of a named range, or None when this (older) template has no such sheet or range.

    `header` names a column the header row must contain; a range starting on the first data row is stepped up one row.
    """
    if sheet_title not in workbook.sheetnames:
        return None
    sheet = workbook[sheet_title]
    ref = None
    if range_name in workbook.defined_names:
        ref = workbook.defined_names[range_name].attr_text
    elif range_name in sheet.defined_names:
        ref = sheet.defined_names[range_name].attr_text
    if ref:
        _, _, coord = ref.rpartition("!")
        _, min_row, _, _ = range_boundaries(coord.replace("$", ""))
        if header and header not in RowSheet(sheet, min_row).columns and min_row > 1:
            min_row -= 1
        return RowSheet(sheet, min_row)
    if fallback_header_row:
        return RowSheet(sheet, fallback_header_row)
    return None


def inline_custom_properties(pairs) -> Optional[List[CustomProperty]]:
    """Custom properties from (property name, cell value) pairs; an empty cell means the row has no such property"""
    properties = [
        CustomProperty(property=cell_text(key), value=resolve_cell_value(value))
        for key, value in pairs
        if cell_text(key) and cell_text(value)
    ]
    return properties or None


def cell_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def split_list(text: Optional[str]) -> Optional[List[str]]:
    if not text:
        return None
    return [item.strip() for item in text.split(",") if item.strip()] or None


# --- Schema sheets -------------------------------------------------------------------------------


def import_schemas(workbook) -> Optional[List[SchemaObject]]:
    """Extract schema information from sheets starting with 'Schema '"""
    schemas = []

    for sheet_name in workbook.sheetnames:
        if sheet_name.startswith("Schema ") and sheet_name != "Schema <table_name>":
            sheet = workbook[sheet_name]
            schema_name = get_cell_value_by_name_in_sheet(sheet, "schema.name")

            if not schema_name:
                continue

            schema = SchemaObject(
                name=schema_name,
                logicalType="object",
                physicalType=get_cell_value_by_name_in_sheet(sheet, "schema.physicalType"),
                physicalName=get_cell_value_by_name_in_sheet(sheet, "schema.physicalName"),
                description=get_cell_value_by_name_in_sheet(sheet, "schema.description"),
                businessName=get_cell_value_by_name_in_sheet(sheet, "schema.businessName"),
                dataGranularityDescription=get_cell_value_by_name_in_sheet(sheet, "schema.dataGranularityDescription"),
                id=get_cell_value_by_name_in_sheet(sheet, "schema.id"),
                deprecated=parse_boolean(get_cell_value_by_name_in_sheet(sheet, "schema.deprecated")),
                context=context_from(get_cell_value_by_name_in_sheet(sheet, "schema.context.instructions"), None, None),
                properties=import_properties(sheet),
                tags=split_list(get_cell_value_by_name_in_sheet(sheet, "schema.tags")),
            )
            schemas.append(schema)

    return schemas if schemas else None


def properties_header_row(sheet: Worksheet) -> Optional[int]:
    properties_range = get_range_by_name_in_sheet(sheet, "schema.properties")
    return properties_range[0] if properties_range else None


def import_properties(sheet) -> Optional[List[SchemaProperty]]:
    """Extract properties from the schema sheet"""
    header_row = properties_header_row(sheet)
    if not header_row:
        return None
    try:
        table = RowSheet(sheet, header_row)
        property_lookup = {}  # full dotted name -> property, for nesting

        for row in table.rows():
            property_name = row.text("property")
            if not property_name:
                continue

            property_obj = SchemaProperty(
                name=property_name,
                logicalType=row.text("logical type"),
                logicalTypeOptions=import_logical_type_options(row),
                physicalType=row.text("physical type"),
                physicalName=row.text("physical name"),
                description=row.text("description"),
                businessName=row.text("business name"),
                required=parse_boolean(row.text("required")),
                unique=parse_boolean(row.text("unique")),
                primaryKey=parse_boolean(row.text("primary key")),
                primaryKeyPosition=parse_integer(row.text("primary key position")),
                partitioned=parse_boolean(row.text("partitioned")),
                partitionKeyPosition=parse_integer(row.text("partition key position")),
                criticalDataElement=parse_boolean(row.text("critical data element status")),
                classification=row.text("classification"),
                transformLogic=row.text("transform logic"),
                transformDescription=row.text("transform description"),
                transformSourceObjects=split_list(row.text("transform sources")),
                encryptedName=row.text("encrypted name"),
                examples=parse_examples(row, row.text("logical type")),
                semanticType=row.text("semantic type"),
                deprecated=parse_boolean(row.text("deprecated")),
                id=row.text("id"),
                tags=split_list(row.text("tags")),
                customProperties=row.custom_properties(),
            )

            # legacy inline definition; the Authoritative Definitions sheet may add more
            authoritative_definition_url = row.text("authoritative definition url")
            authoritative_definition_type = row.text("authoritative definition type")
            if authoritative_definition_url and authoritative_definition_type:
                property_obj.authoritativeDefinitions = [
                    AuthoritativeDefinition(url=authoritative_definition_url, type=authoritative_definition_type)
                ]

            property_lookup[property_name] = property_obj

        root_properties = []
        for name, prop in property_lookup.items():
            if "." in name:
                parent_name, child_name = name.rsplit(".", 1)
                if parent_name in property_lookup:
                    parent_prop = property_lookup[parent_name]
                    prop.name = child_name
                    if parent_prop.logicalType == "array":
                        prop.name = None  # the row "<parent>.items" names the array's items
                        parent_prop.items = prop
                    else:
                        if parent_prop.properties is None:
                            parent_prop.properties = []
                        parent_prop.properties.append(prop)
            else:
                root_properties.append(prop)

        return root_properties if root_properties else None
    except Exception as e:
        logger.warning(f"Error importing properties: {str(e)}")
        return None


def import_logical_type_options(row: Row):
    """Import logical type options from property row"""
    logical_type_options_dict = {
        "minLength": parse_integer(row.text("minimum length")),
        "maxLength": parse_integer(row.text("maximum length")),
        "pattern": row.text("pattern"),
        "format": row.text("format"),
        "exclusiveMaximum": resolve_cell_value(row.raw("exclusive maximum")),
        "exclusiveMinimum": resolve_cell_value(row.raw("exclusive minimum")),
        "minimum": resolve_cell_value(row.raw("minimum")),
        "maximum": resolve_cell_value(row.raw("maximum")),
        "multipleOf": resolve_cell_value(row.raw("multiple of")),
        "minItems": parse_integer(row.text("minimum items")),
        "maxItems": parse_integer(row.text("maximum items")),
        "uniqueItems": parse_boolean(row.text("unique items")),
        "maxProperties": parse_integer(row.text("maximum properties")),
        "minProperties": parse_integer(row.text("minimum properties")),
        "required": split_list(row.text("required properties")),
        "dimensions": parse_integer(row.text("dimensions")),
        "elementType": row.text("element type"),
        "distanceMetric": row.text("distance metric"),
        "normalized": parse_boolean(row.text("normalized")),
        "embeddingModel": row.text("embedding model"),
        "embeddingModelVersion": row.text("embedding model version"),
    }
    options = {key: value for key, value in logical_type_options_dict.items() if value is not None}
    return options or None


def parse_boolean(value):
    """Parse a string value to boolean"""
    if value is None:
        return None
    value = value.lower().strip()
    return value == "true" or value == "yes" or value == "1"


def parse_port(value):
    """Parse a port cell: an integer, or a string such as a ``${DB_PORT}`` reference (ODCS v3.2.0)."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value).strip()
    if not text:
        return None
    return int(text) if text.isdigit() else text


def parse_integer(value):
    """Parse a string value to integer"""
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def get_range_by_name_in_sheet(sheet: Worksheet, name: str) -> tuple | None:
    """Find the range (start_row, end_row) of a worksheet-scoped named range"""
    try:
        if name in sheet.defined_names:
            for sheet_title, range_address in sheet.defined_names[name].destinations:
                if sheet_title == sheet.title:
                    min_col, min_row, max_col, max_row = range_boundaries(range_address.replace("$", ""))
                    return (min_row, max_row)
    except Exception as e:
        logger.warning(f"Error finding range by name {name}: {str(e)}")
    return None


def get_cell_by_name_in_workbook(workbook: Workbook, name: str) -> Cell | None:
    """Find a cell by a workbook-scoped name"""
    try:
        if name in workbook.defined_names:
            for sheet_title, coordinate in workbook.defined_names[name].destinations:
                return workbook[sheet_title][coordinate.split(":")[0]]
    except Exception as e:
        logger.warning(f"Error finding cell by name {name}: {str(e)}")
    return None


def get_cell_value_by_name(workbook: Workbook, name: str) -> str | None:
    """Get the text of a named cell; None when the template has no such cell"""
    cell = get_cell_by_name_in_workbook(workbook, name)
    return cell_text(cell.value) if cell is not None else None


def get_cell_value_by_name_in_sheet(sheet: Worksheet, name: str) -> str | None:
    """Get the text of a worksheet-scoped named cell"""
    try:
        if name in sheet.defined_names:
            for sheet_title, coordinate in sheet.defined_names[name].destinations:
                if sheet_title == sheet.title:
                    return cell_text(sheet[coordinate].value)
    except Exception as e:
        logger.warning(f"Error getting cell value by name {name} in sheet {sheet.title}: {str(e)}")
    return None


# --- Support, team, roles, SLA, servers, pricing -------------------------------------------------


def import_support(workbook: Workbook) -> Optional[List[Support]]:
    table = open_row_sheet(workbook, "Support", "support")
    if not table:
        return None
    support_channels = []
    for row in table.rows():
        channel = row.text("channel")
        if not channel:
            continue
        support_channels.append(
            Support(
                channel=channel,
                url=row.text("channel url"),
                description=row.text("description"),
                tool=row.text("tool"),
                scope=row.text("scope"),
                invitationUrl=row.text("invitation url"),
                id=row.text("id"),
                customProperties=row.custom_properties(),
            )
        )
    return support_channels or None


def import_team(workbook: Workbook):
    """The team: a list of members, or a Team block when the template's team cells are filled"""
    members = []
    table = open_row_sheet(workbook, "Team", "team")
    if table:
        for row in table.rows():
            username = row.text("username")
            name = row.text("name")
            role = row.text("role")
            if not (username or name or role):
                continue
            members.append(
                TeamMember(
                    username=username,
                    name=name,
                    description=row.text("description"),
                    role=role,
                    dateIn=row.text("date in"),
                    dateOut=row.text("date out"),
                    replacedByUsername=row.text("replaced by username"),
                    id=row.text("id"),
                    customProperties=row.custom_properties(),
                )
            )
    team_name = get_cell_value_by_name(workbook, "team.name")
    team_description = get_cell_value_by_name(workbook, "team.description")
    team_tags = split_list(get_cell_value_by_name(workbook, "team.tags"))
    team_id = get_cell_value_by_name(workbook, "team.id")
    if team_name or team_description or team_tags or team_id:
        return Team(name=team_name, description=team_description, tags=team_tags, id=team_id, members=members or None)
    return members or None


def import_roles(workbook: Workbook) -> Optional[List[Role]]:
    table = open_row_sheet(workbook, "Roles", "roles", fallback_header_row=4)
    if not table:
        return None
    roles_list = []
    for row in table.rows():
        role_name = row.text("role")
        if not role_name:
            continue
        roles_list.append(
            Role(
                role=role_name,
                description=row.text("description"),
                access=row.text("access"),
                firstLevelApprovers=row.text("1st level approvers"),
                secondLevelApprovers=row.text("2nd level approvers"),
                id=row.text("id"),
                customProperties=row.custom_properties(),
            )
        )
    return roles_list or None


def import_sla_properties(workbook: Workbook) -> Optional[List[ServiceLevelAgreementProperty]]:
    table = open_row_sheet(workbook, "SLA", "slaProperties", fallback_header_row=6)
    if not table:
        return None
    sla_properties = []
    for row in table.rows():
        property_name = row.text("property")
        if not property_name:
            continue
        sla_properties.append(
            ServiceLevelAgreementProperty(
                property=property_name,
                value=resolve_cell_value(row.raw("value")),
                valueExt=resolve_cell_value(row.raw("extended value")),
                unit=row.text("unit"),
                element=row.text("element"),
                driver=row.text("driver"),
                description=row.text("description"),
                scheduler=row.text("scheduler"),
                schedule=row.text("schedule"),
                id=row.text("id"),
                customProperties=row.custom_properties(),
            )
        )
    return sla_properties or None


def import_servers(workbook) -> Optional[List[Server]]:
    """Servers are laid out horizontally: one column per server, one row per field"""
    if "Servers" not in workbook.sheetnames:
        return None
    sheet = workbook["Servers"]
    server_cell = get_cell_by_name_in_workbook(workbook, "servers.server")
    if not server_cell:
        return None

    label_row = next(
        (
            r
            for r in range(1, last_row(sheet, 1, (1,)) + 1)
            if (cell_text(sheet.cell(row=r, column=1).value) or "").startswith(CUSTOM_PROPERTIES_GROUP)
        ),
        None,
    )
    # a template without the group label has no custom property rows, only the per-type server blocks
    property_rows = range(label_row + 1, last_row(sheet, label_row + 1, (2,)) + 1) if label_row else range(0)
    servers = []
    index = 0
    while True:
        column = server_cell.column + index
        server_name = cell_text(sheet.cell(row=server_cell.row, column=column).value)
        if not server_name:
            break
        server = Server(
            server=server_name,
            description=get_server_cell_value(workbook, sheet, "servers.description", index),
            environment=get_server_cell_value(workbook, sheet, "servers.environment", index),
            type=get_server_cell_value(workbook, sheet, "servers.type", index),
            id=get_server_cell_value(workbook, sheet, "servers.id", index),
        )
        for field in SERVER_FIELDS:
            name = server_field_name(workbook, server.type, field)
            if not name:
                continue
            value = get_server_cell_value(workbook, sheet, name, index)
            if field == "port":
                value = parse_port(value)
            setattr(server, "schema_" if field == "schema" else field, value)
        server.customProperties = inline_custom_properties(
            [(sheet.cell(row=row, column=2).value, sheet.cell(row=row, column=column).value) for row in property_rows]
        )
        servers.append(server)
        index += 1
    return servers or None


def get_server_cell_value(workbook: Workbook, sheet: Worksheet, name: str, col_offset: int):
    cell = get_cell_by_name_in_workbook(workbook, name)
    if not cell:
        return None
    return cell_text(sheet.cell(row=cell.row, column=cell.column + col_offset).value)


def import_price(workbook) -> Optional[Dict[str, Any]]:
    price_amount = get_cell_value_by_name(workbook, "price.priceAmount")
    price_currency = get_cell_value_by_name(workbook, "price.priceCurrency")
    price_unit = get_cell_value_by_name(workbook, "price.priceUnit")
    if not (price_amount or price_currency or price_unit):
        return None
    return {
        "priceAmount": price_amount,
        "priceCurrency": price_currency,
        "priceUnit": price_unit,
        "id": get_cell_value_by_name(workbook, "price.id"),
    }


# --- Custom properties and authoritative definitions ---------------------------------------------


def import_root_custom_properties(workbook: Workbook) -> Optional[List[CustomProperty]]:
    """The contract's own custom properties: the Owner cell, plus a pre-3.2 Custom Properties sheet without element references"""
    custom_properties = []
    owner = get_cell_value_by_name(workbook, "owner")
    if owner:
        custom_properties.append(CustomProperty(property="owner", value=owner))

    table = open_row_sheet(workbook, "Custom Properties", "CustomProperties", header="property")
    if table and "scope" not in table.columns:
        for row in table.rows():
            property_name = row.text("property")
            if not property_name or property_name == "owner":
                continue
            custom_properties.append(CustomProperty(property=property_name, value=resolve_cell_value(row.raw("value"))))

    return custom_properties or None


def attach_custom_properties(odcs: OpenDataContractStandard, workbook: Workbook):
    """Rows of the Custom Properties sheet, joined to the element they reference; the sheet wins over an inline pair"""
    table = open_row_sheet(workbook, "Custom Properties", "CustomProperties", header="property")
    if not table or "scope" not in table.columns:
        return
    for row in table.rows():
        property_name = row.text("property")
        if not property_name or not row.text("scope"):
            continue
        if row.text("scope") == "Contract" and property_name == "owner":
            if not (row.text("description") or row.text("vendor") or row.text("id")):
                continue  # the Owner cell on Fundamentals holds it
        element = resolve_element(odcs, row, "custom property")
        if element is None:
            continue
        try:
            value = resolve_cell_value(row.raw("value"), row.text("value type"))
        except ValueError as e:
            logger.warning(f"Custom property {property_name} on row {row.row_index} has an invalid JSON value: {e}")
            continue
        prop = CustomProperty(
            property=property_name,
            value=value,
            description=row.text("description"),
            vendor=row.text("vendor"),
            id=row.text("id"),
        )
        merge_custom_property(element, prop, f"{row.text('scope')} {row.text('scope name') or ''}".strip())


def merge_custom_property(element, prop: CustomProperty, element_label: str):
    existing = element.customProperties or []
    for index, current in enumerate(existing):
        if current.property == prop.property:
            if element_label == "Contract" and prop.property == "owner":
                prop.value = prop.value if prop.value is not None else current.value
                existing[index] = prop
                return
            logger.warning(
                f"Custom property {prop.property} of {element_label} is both inline and on the Custom Properties sheet; "
                "the sheet overrides it."
            )
            existing[index] = prop
            element.customProperties = existing
            return
    element.customProperties = existing + [prop]


def attach_authoritative_definitions(odcs: OpenDataContractStandard, workbook: Workbook):
    table = open_row_sheet(workbook, "Authoritative Definitions", "authoritativeDefinitions")
    if not table:
        return
    for row in table.rows():
        url = row.text("url")
        if not url:
            continue
        element = resolve_element(odcs, row, "authoritative definition")
        if element is None:
            continue
        definition = AuthoritativeDefinition(
            url=url, type=row.text("type"), description=row.text("description"), id=row.text("id")
        )
        existing = element.authoritativeDefinitions or []
        if any(current.url == url for current in existing):
            continue  # the legacy inline definition of a property
        element.authoritativeDefinitions = existing + [definition]


def resolve_element(odcs: OpenDataContractStandard, row: Row, what: str):
    """The element a child-sheet row references, or None (with a warning) when it cannot be found"""
    kind = row.text("scope")
    ref = row.text("scope name") or ""
    if kind == "Description" and odcs.description is None:
        odcs.description = Description()
    if kind == "Team" and not isinstance(odcs.team, Team):
        odcs.team = Team(members=odcs.team or None)
    element = element_index(odcs).get((kind, ref))
    if element is None:
        logger.warning(
            f"Row {row.row_index} of the {row.row_sheet.sheet.title} sheet references {kind} '{ref}', which does not exist; the {what} was dropped"
        )
        return None
    return element.obj


# --- Enum, synonyms, context ---------------------------------------------------------------------


def find_property(schemas, schema_name, property_path):
    """The property of a schema by its dotted path, "<parent>.items" naming array items"""
    schema = next((s for s in schemas or [] if s.name == schema_name), None)
    if schema is None or not property_path:
        return schema, None
    properties = schema.properties or []
    current = None
    for segment in property_path.split("."):
        if segment == "items" and current is not None and current.items is not None:
            current = current.items
        else:
            current = next((p for p in properties if p.name == segment), None)
        if current is None:
            return schema, None
        properties = current.properties or []
    return schema, current


def attach_enum_values(schemas, workbook: Workbook):
    table = open_row_sheet(workbook, "Enums", "enum")
    if not table:
        return
    for row in table.rows():
        schema_name, property_path = row.text("schema"), row.text("property")
        if not schema_name:
            continue
        schema, prop = find_property(schemas, schema_name, property_path)
        if prop is None:
            logger.warning(f"Enums row {row.row_index}: property {schema_name}.{property_path} does not exist; dropped")
            continue
        value = row.raw("value")
        if isinstance(value, float) and value.is_integer():
            value = int(value)
        enum_value = EnumValue(
            value=value.strip() if isinstance(value, str) else value,
            label=row.text("label"),
            description=row.text("description"),
            tags=split_list(row.text("tags")),
            id=row.text("id"),
            customProperties=row.custom_properties(),
        )
        prop.enum = (prop.enum or []) + [enum_value]


def attach_synonyms(schemas, workbook: Workbook):
    table = open_row_sheet(workbook, "Synonyms", "synonyms")
    if not table:
        return
    for row in table.rows():
        schema_name, property_path, synonym_text = row.text("schema"), row.text("property"), row.text("synonym")
        if not schema_name or not synonym_text:
            continue
        schema, prop = find_property(schemas, schema_name, property_path)
        owner = prop if property_path else schema
        if owner is None:
            logger.warning(f"Synonyms row {row.row_index}: {schema_name}.{property_path or ''} does not exist; dropped")
            continue
        synonym = Synonym(
            synonym=synonym_text,
            description=row.text("description"),
            locale=row.text("locale"),
            source=row.text("source"),
            status=row.text("status"),
            id=row.text("id"),
            customProperties=row.custom_properties(),
        )
        owner.synonyms = (owner.synonyms or []) + [synonym]


def context_from(instructions, statements, constraints):
    if not (instructions or statements or constraints):
        return None
    return Context(instructions=instructions, verifiedStatements=statements or None, constraints=constraints or None)


def attach_context_statements(odcs: OpenDataContractStandard, workbook: Workbook):
    statements = open_row_sheet(workbook, "Verified Statements", "verifiedStatements")
    constraints = open_row_sheet(workbook, "Constraints", "constraints")
    for table, field, key in (
        (statements, "verifiedStatements", "question"),
        (constraints, "constraints", "constraint"),
    ):
        if not table:
            continue
        for row in table.rows():
            text = row.text(key)
            if not text:
                continue
            level, schema_name = (row.text("scope") or "").lower(), row.text("schema name")
            owner = odcs
            if level == "schema" or schema_name:
                owner = next((s for s in odcs.schema_ or [] if s.name == schema_name), None)
                if owner is None:
                    logger.warning(
                        f"{table.sheet.title} row {row.row_index}: schema {schema_name} does not exist; dropped"
                    )
                    continue
            if field == "verifiedStatements":
                item = VerifiedStatement(question=text, answer=row.text("answer"))
            else:
                item = Constraint(constraint=text)
            item.tags = split_list(row.text("tags"))
            item.id = row.text("id")
            item.customProperties = row.custom_properties()
            context = owner.context
            if context is None or isinstance(context, str):
                context = Context(instructions=context)
            setattr(context, field, (getattr(context, field) or []) + [item])
            owner.context = context


# --- Quality -------------------------------------------------------------------------------------


def import_quality(workbook: Workbook) -> Dict[str, List[DataQuality]]:
    """Quality rows keyed by "schema" or "schema.property" """
    table = open_row_sheet(workbook, "Quality", "quality")
    if not table:
        return {}
    quality_map = {}
    for row in table.rows():
        schema_name = row.text("schema")
        property_name = row.text("property")
        quality_type = row.text("quality type")
        description = row.text("description")
        rule = row.text("metric (library)")
        if not schema_name or (not quality_type and not description and not rule):
            continue
        threshold_dict = parse_threshold_values(row.text("threshold operator"), row.text("threshold value"))
        # a custom check is written verbatim: its trailing newline is part of the implementation
        implementation = row.raw("implementation (custom)")
        quality = DataQuality(
            name=row.text("name"),
            description=description,
            type=quality_type,
            metric=rule,
            dimension=row.text("dimension"),
            method=row.text("method"),
            businessImpact=row.text("business impact"),
            unit=row.text("unit"),
            tags=split_list(row.text("tags")),
            arguments=parse_arguments(row.text("arguments")),
            query=row.text("query (sql)"),
            engine=row.text("quality engine (custom)"),
            implementation=None if implementation is None else str(implementation),
            severity=row.text("severity"),
            scheduler=row.text("scheduler"),
            schedule=row.text("schedule"),
            id=row.text("id"),
            customProperties=row.custom_properties(),
            **threshold_dict,
        )
        key = schema_name if not property_name else f"{schema_name}.{property_name}"
        quality_map.setdefault(key, []).append(quality)
    return quality_map


def parse_examples(row, logical_type: Optional[str]) -> Optional[List[Any]]:
    """Examples keep the cell verbatim on a string property and resolve on any other type."""
    if logical_type in (None, "string", "object", "array", "map"):
        return split_list(row.text("example(s)"))
    values = split_list(row.text("example(s)"))
    return None if values is None else [resolve_cell_value(value) for value in values]


def parse_arguments(text: Optional[str]) -> Optional[dict]:
    """The Arguments cell of a library quality rule, a JSON object."""
    if not text:
        return None
    try:
        return json.loads(text)
    except ValueError as e:
        logger.warning(f"Quality arguments are not valid JSON: {text} ({e})")
        return None


def parse_threshold_values(threshold_operator: str, threshold_value: str) -> Dict[str, Any]:
    """Parse threshold operator and value into DataQuality threshold fields"""
    threshold_dict = {}

    if not threshold_operator or not threshold_value:
        return threshold_dict

    if threshold_operator in ["mustBeBetween", "mustNotBeBetween"]:
        content = threshold_value[1:-1] if threshold_value.startswith("[") else threshold_value
        if True:
            try:
                values = [resolve_cell_value(v.strip()) for v in content.split(",") if v.strip()]
                if len(values) >= 2:
                    threshold_dict[threshold_operator] = values[:2]
            except (ValueError, TypeError) as e:
                logger.warning(f"Failed to parse between values: {threshold_value}, error: {e}")
    else:
        try:
            isFraction = "." in threshold_value
            if threshold_value.replace(".", "").replace("-", "").isdigit():
                threshold_dict[threshold_operator] = float(threshold_value) if isFraction else int(threshold_value)
        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to parse threshold value: {threshold_value}, error: {e}")

    return threshold_dict


def attach_quality_to_schemas(
    schemas: Optional[List[SchemaObject]], quality_map: Dict[str, List[DataQuality]]
) -> Optional[List[SchemaObject]]:
    if not schemas:
        return None
    for schema in schemas:
        if not schema.name:
            continue
        schema_quality = quality_map.get(schema.name)
        if schema_quality:
            schema.quality = schema_quality
        if schema.properties:
            schema.properties = attach_quality_to_properties(schema.properties, schema.name, quality_map)
    return schemas


def attach_quality_to_properties(
    properties: List[SchemaProperty], schema_name: str, quality_map: Dict[str, List[DataQuality]], prefix: str = ""
) -> List[SchemaProperty]:
    for prop in properties:
        if not prop.name:
            continue
        full_property_name = f"{prefix}.{prop.name}" if prefix else prop.name
        property_quality = quality_map.get(f"{schema_name}.{full_property_name}")
        if property_quality:
            prop.quality = property_quality
        if prop.properties:
            prop.properties = attach_quality_to_properties(
                prop.properties, schema_name, quality_map, full_property_name
            )
        if prop.items:
            items_quality = quality_map.get(f"{schema_name}.{full_property_name}.items")
            if items_quality:
                prop.items.quality = items_quality
            if prop.items.properties:
                prop.items.properties = attach_quality_to_properties(
                    prop.items.properties, schema_name, quality_map, f"{full_property_name}.items"
                )
    return properties


# --- Relationships -------------------------------------------------------------------------------


def attach_relationships(schemas, workbook: Workbook):
    """Rows of the Relationships sheet: schema-level ones belong to the first schema named in From (then To)"""
    table = open_row_sheet(workbook, "Relationships", "relationships")
    if not table or not schemas:
        return
    schema_names = {s.name for s in schemas}
    for row in table.rows():
        from_text = row.text("from")
        if not from_text:
            continue
        level = (row.text("level") or "").lower()
        common = {"type": row.text("type"), "id": row.text("id"), "customProperties": row.custom_properties()}
        if level == "schema":
            from_value, to_value = split_refs(from_text), split_refs(row.text("to"))
            candidates = [as_list(from_value)[0] if from_value else None, as_list(to_value)[0] if to_value else None]
            owner_name = next((c.split(".")[0] for c in candidates if c and c.split(".")[0] in schema_names), None)
            if owner_name is None:
                logger.warning(f"Relationships row {row.row_index} references no imported schema; dropped")
                continue
            owner = next(s for s in schemas if s.name == owner_name)
            relationship = Relationship(**{"from": from_value, "to": to_value}, **common)
        else:
            schema_name, _, property_path = from_text.partition(".")
            _, owner = find_property(schemas, schema_name, property_path)
            if owner is None:
                logger.warning(f"Relationships row {row.row_index}: property {from_text} does not exist; dropped")
                continue
            relationship = Relationship(to=split_refs(row.text("to")), **common)
        owner.relationships = (owner.relationships or []) + [relationship]


def split_refs(text: Optional[str]):
    """A comma-separated cell as a list, a single reference as a string"""
    if not text:
        return None
    refs = [part.strip() for part in text.split(",") if part.strip()]
    return refs[0] if len(refs) == 1 else refs


def as_list(value) -> list:
    return value if isinstance(value, list) else [value]
