import logging
import os
from typing import Any, Dict, List, Optional

import openpyxl
from open_data_contract_standard.model import (
    CustomProperty,
    OpenDataContractStandard,
    Role,
    SchemaObject,
    SchemaProperty,
    Server,
    ServiceLevelAgreementProperty,
    Support,
    Team,
)
from openpyxl.workbook.workbook import Workbook

from datacontract.imports.importer import Importer
from datacontract.imports.odcs_v3_importer import import_from_odcs_model
from datacontract.model.data_contract_specification import (
    DataContractSpecification,
)
from datacontract.model.exceptions import DataContractException

logger = logging.getLogger(__name__)


class ExcelImporter(Importer):
    def import_source(
        self, data_contract_specification: DataContractSpecification, source: str, import_args: dict
    ) -> DataContractSpecification:
        return import_excel(data_contract_specification, source)


def import_excel(data_contract_specification: DataContractSpecification, source: str) -> DataContractSpecification:
    try:
        odcs = import_excel_as_odcs(source)
        return import_from_odcs_model(data_contract_specification, odcs)
    except Exception as e:
        raise DataContractException(
            type="schema",
            name="Parse excel contract",
            reason=f"Failed to parse odcs contract from {source}",
            engine="datacontract",
            original_exception=e,
        )


def import_excel_as_odcs(excel_file_path: str) -> OpenDataContractStandard:
    """
    Import an Excel file and convert it to an OpenDataContractStandard object

    Args:
        excel_file_path: Path to the Excel file

    Returns:
        OpenDataContractStandard object
    """
    if not os.path.exists(excel_file_path):
        raise FileNotFoundError(f"Excel file not found: {excel_file_path}")

    try:
        workbook = openpyxl.load_workbook(excel_file_path, data_only=True)
    except Exception as e:
        raise DataContractException(
            type="schema",
            name="Parse excel contract",
            reason=f"Failed to open Excel file: {excel_file_path}",
            engine="datacontract",
            original_exception=e,
        )

    try:
        # Get basic information
        owner = get_cell_value_by_name(workbook, "owner")

        # Get description values
        purpose = get_cell_value_by_name(workbook, "description.purpose")
        limitations = get_cell_value_by_name(workbook, "description.limitations")
        usage = get_cell_value_by_name(workbook, "description.usage")

        # Build description dict
        description = None
        if purpose or limitations or usage:
            description = {"purpose": purpose, "limitations": limitations, "usage": usage}

        # Get tags as a list
        tags_str = get_cell_value_by_name(workbook, "tags")
        tags = None
        if tags_str:
            tags = [tag.strip() for tag in tags_str.split(",") if tag.strip()]

        # Import other components
        schemas = import_schemas(workbook)
        support = import_support(workbook)
        team = import_team(workbook)
        roles = import_roles(workbook)
        sla_properties = import_sla_properties(workbook)
        servers = import_servers(workbook)
        price = import_price(workbook)
        custom_properties = import_custom_properties(owner, workbook)

        # Create the ODCS object with proper object creation
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
            tags=tags,
            schema=schemas,
            support=support,
            price=price,
            team=team,
            roles=roles,
            slaDefaultElement=get_cell_value_by_name(workbook, "slaDefaultElement"),
            slaProperties=sla_properties,
            servers=servers,
            customProperties=custom_properties,
        )

        return odcs
    except Exception as e:
        logger.error(f"Error importing Excel file: {str(e)}")
        raise DataContractException(
            type="schema",
            name="Parse excel contract",
            reason=f"Failed to parse Excel file: {excel_file_path}",
            engine="datacontract",
            original_exception=e,
        )
    finally:
        workbook.close()


def get_cell_value_by_name(workbook: Workbook, name: str) -> Optional[str]:
    """Get the value of a named cell"""
    try:
        for named_range in workbook.defined_names:
            if named_range == name:
                # Named ranges are in the format SheetName!A1
                destinations = workbook.defined_names[named_range].destinations
                for sheet_title, coordinate in destinations:
                    sheet = workbook[sheet_title]
                    cell = sheet[coordinate]
                    if cell.value is not None:
                        return str(cell.value)
    except Exception as e:
        logger.debug(f"Error getting cell value by name {name}: {str(e)}")
    return None


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
                authoritativeDefinitions=None,
                properties=import_properties(sheet),
                quality=None,
                customProperties=None,
                tags=None,
            )

            # Get tags
            tags_str = get_cell_value_by_name_in_sheet(sheet, "schema.tags")
            if tags_str:
                schema.tags = [tag.strip() for tag in tags_str.split(",") if tag.strip()]

            schemas.append(schema)

    return schemas if schemas else None


def get_cell_value_by_name_in_sheet(sheet, name: str) -> Optional[str]:
    """Get the value of a named cell within a specific sheet"""
    try:
        workbook = sheet.parent
        for named_range in workbook.defined_names.definedName:
            if named_range.name == name:
                destinations = named_range.destinations
                for sheet_title, coordinate in destinations:
                    if sheet_title == sheet.title:
                        cell = sheet[coordinate]
                        if cell.value is not None:
                            return str(cell.value)
    except Exception as e:
        logger.debug(f"Error getting cell value by name {name} in sheet {sheet.title}: {str(e)}")
    return None


def import_properties(sheet) -> Optional[List[SchemaProperty]]:
    """Extract properties from the schema sheet"""
    properties = []

    try:
        # Find the properties table
        properties_range = find_range_by_name(sheet, "schema.properties")
        if not properties_range:
            return None

        # Get header row to map column names to indices
        header_row = list(sheet.rows)[properties_range[0] - 1]  # Convert to 0-based indexing
        headers = {}
        for i, cell in enumerate(header_row):
            if cell.value:
                headers[cell.value.lower()] = i

        # Process property rows
        for row_idx in range(properties_range[0], properties_range[1]):
            row = list(sheet.rows)[row_idx]

            # Skip empty rows or header row
            property_name = get_cell_value(row, headers.get("property"))
            if not property_name or row_idx == properties_range[0] - 1:
                continue

            # Create property object
            property_obj = SchemaProperty(
                name=property_name,
                logicalType=get_cell_value(row, headers.get("logical type")),
                physicalType=get_cell_value(row, headers.get("physical type")),
                physicalName=get_cell_value(row, headers.get("physical name")),
                description=get_cell_value(row, headers.get("description")),
                businessName=get_cell_value(row, headers.get("business name")),
                required=parse_boolean(get_cell_value(row, headers.get("required"))),
                unique=parse_boolean(get_cell_value(row, headers.get("unique"))),
                primaryKey=parse_boolean(get_cell_value(row, headers.get("primary key"))),
                primaryKeyPosition=parse_integer(get_cell_value(row, headers.get("primary key position"))),
                partitioned=parse_boolean(get_cell_value(row, headers.get("partitioned"))),
                partitionKeyPosition=parse_integer(get_cell_value(row, headers.get("partition key position"))),
                criticalDataElement=parse_boolean(get_cell_value(row, headers.get("critical data element status"))),
                classification=get_cell_value(row, headers.get("classification")),
                transformLogic=get_cell_value(row, headers.get("transform logic")),
                transformDescription=get_cell_value(row, headers.get("transform description")),
                encryptedName=get_cell_value(row, headers.get("encrypted name")),
                authoritativeDefinitions=None,
                properties=None,
                quality=None,
                customProperties=None,
                items=None,
            )

            # Tags
            tags_value = get_cell_value(row, headers.get("tags"))
            if tags_value:
                property_obj.tags = [tag.strip() for tag in tags_value.split(",") if tag.strip()]

            # Transform sources
            transform_sources = get_cell_value(row, headers.get("transform sources"))
            if transform_sources:
                property_obj.transformSourceObjects = [
                    src.strip() for src in transform_sources.split(",") if src.strip()
                ]

            # Examples
            examples = get_cell_value(row, headers.get("example(s)"))
            if examples:
                property_obj.examples = [ex.strip() for ex in examples.split(",") if ex.strip()]

            # Add property to list
            properties.append(property_obj)
    except Exception as e:
        logger.debug(f"Error importing properties: {str(e)}")
        return None

    return properties if properties else None


def parse_boolean(value):
    """Parse a string value to boolean"""
    if value is None:
        return None
    value = value.lower().strip()
    return value == "true" or value == "yes" or value == "1"


def parse_integer(value):
    """Parse a string value to integer"""
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def find_range_by_name(sheet, name: str) -> Optional[tuple]:
    """Find the range (start_row, end_row) of a named range in a sheet"""
    try:
        workbook = sheet.parent
        for named_range in workbook.defined_names.definedName:
            if named_range.name == name:
                destinations = named_range.destinations
                for sheet_title, range_address in destinations:
                    if sheet_title == sheet.title:
                        # For named ranges that refer to entire rows or multiple rows
                        if ":" in range_address:
                            # Convert Excel range to row numbers
                            start_ref, end_ref = range_address.split(":")
                            start_row = int("".join(filter(str.isdigit, start_ref)))
                            end_row = int("".join(filter(str.isdigit, end_ref)))
                            return (start_row, end_row)
                        else:
                            # Single cell
                            row = int("".join(filter(str.isdigit, range_address)))
                            return (row, row)
    except Exception as e:
        logger.debug(f"Error finding range by name {name}: {str(e)}")
    return None


def get_cell_value(row, col_idx):
    """Safely get cell value from a row by column index"""
    if col_idx is None:
        return None
    try:
        cell = row[col_idx]
        return str(cell.value) if cell.value is not None else None
    except (IndexError, AttributeError):
        return None


def import_support(workbook) -> Optional[List[Support]]:
    """Extract support information from the Support sheet"""
    try:
        support_sheet = workbook.get("Support")
        if not support_sheet:
            return None

        support_range = find_range_by_name(support_sheet, "support")
        if not support_range:
            return None

        header_row = list(support_sheet.rows)[support_range[0] - 1]
        headers = {}
        for i, cell in enumerate(header_row):
            if cell.value:
                headers[cell.value.lower()] = i

        support_channels = []
        for row_idx in range(support_range[0], support_range[1]):
            row = list(support_sheet.rows)[row_idx]

            channel = get_cell_value(row, headers.get("channel"))
            if not channel or row_idx == support_range[0] - 1:
                continue

            support_channel = Support(
                channel=channel,
                url=get_cell_value(row, headers.get("channel url")),
                description=get_cell_value(row, headers.get("description")),
                tool=get_cell_value(row, headers.get("tool")),
                scope=get_cell_value(row, headers.get("scope")),
                invitationUrl=get_cell_value(row, headers.get("invitation url")),
            )

            support_channels.append(support_channel)
    except Exception as e:
        logger.debug(f"Error importing support: {str(e)}")
        return None

    return support_channels if support_channels else None


def import_team(workbook) -> Optional[List[Team]]:
    """Extract team information from the Team sheet"""
    try:
        team_sheet = workbook.get("Team")
        if not team_sheet:
            return None

        team_range = find_range_by_name(team_sheet, "team")
        if not team_range:
            return None

        header_row = list(team_sheet.rows)[team_range[0] - 1]
        headers = {}
        for i, cell in enumerate(header_row):
            if cell.value:
                headers[cell.value.lower()] = i

        team_members = []
        for row_idx in range(team_range[0], team_range[1]):
            row = list(team_sheet.rows)[row_idx]

            username = get_cell_value(row, headers.get("username"))
            name = get_cell_value(row, headers.get("name"))
            role = get_cell_value(row, headers.get("role"))

            if (not (username or name or role)) or row_idx == team_range[0] - 1:
                continue

            team_member = Team(
                username=username,
                name=name,
                description=get_cell_value(row, headers.get("description")),
                role=role,
                dateIn=get_cell_value(row, headers.get("date in")),
                dateOut=get_cell_value(row, headers.get("date out")),
                replacedByUsername=get_cell_value(row, headers.get("replaced by username")),
            )

            team_members.append(team_member)
    except Exception as e:
        logger.debug(f"Error importing team: {str(e)}")
        return None

    return team_members if team_members else None


def import_roles(workbook) -> Optional[List[Role]]:
    """Extract roles information from the Roles sheet"""
    try:
        roles_sheet = workbook.get("Roles")
        if not roles_sheet:
            return None

        roles_range = find_range_by_name(roles_sheet, "roles")
        if not roles_range:
            return None

        header_row = list(roles_sheet.rows)[roles_range[0] - 1]
        headers = {}
        for i, cell in enumerate(header_row):
            if cell.value:
                headers[cell.value.lower()] = i

        roles_list = []
        for row_idx in range(roles_range[0], roles_range[1]):
            row = list(roles_sheet.rows)[row_idx]

            role_name = get_cell_value(row, headers.get("role"))
            if not role_name or row_idx == roles_range[0] - 1:
                continue

            role = Role(
                role=role_name,
                description=get_cell_value(row, headers.get("description")),
                access=get_cell_value(row, headers.get("access")),
                firstLevelApprovers=get_cell_value(row, headers.get("1st level approvers")),
                secondLevelApprovers=get_cell_value(row, headers.get("2nd level approvers")),
                customProperties=None,
            )

            roles_list.append(role)
    except Exception as e:
        logger.debug(f"Error importing roles: {str(e)}")
        return None

    return roles_list if roles_list else None


def import_sla_properties(workbook) -> Optional[List[ServiceLevelAgreementProperty]]:
    """Extract SLA properties from the SLA sheet"""
    try:
        sla_sheet = workbook.get("SLA")
        if not sla_sheet:
            return None

        sla_range = find_range_by_name(sla_sheet, "slaProperties")
        if not sla_range:
            return None

        header_row = list(sla_sheet.rows)[sla_range[0] - 1]
        headers = {}
        for i, cell in enumerate(header_row):
            if cell.value:
                headers[cell.value.lower()] = i

        sla_properties = []
        for row_idx in range(sla_range[0], sla_range[1]):
            row = list(sla_sheet.rows)[row_idx]

            property_name = get_cell_value(row, headers.get("property"))
            if not property_name or row_idx == sla_range[0] - 1:
                continue

            sla_property = ServiceLevelAgreementProperty(
                property=property_name,
                value=get_cell_value(row, headers.get("value")),
                valueExt=get_cell_value(row, headers.get("extended value")),
                unit=get_cell_value(row, headers.get("unit")),
                element=get_cell_value(row, headers.get("element")),
                driver=get_cell_value(row, headers.get("driver")),
            )

            sla_properties.append(sla_property)
    except Exception as e:
        logger.debug(f"Error importing SLA properties: {str(e)}")
        return None

    return sla_properties if sla_properties else None


def import_servers(workbook) -> Optional[List[Server]]:
    """Extract server information from the Servers sheet"""
    try:
        servers_sheet = workbook.get("Servers")
        if not servers_sheet:
            return None

        # Find the server cells
        server_cell = None
        for named_range in workbook.defined_names.definedName:
            if named_range.name == "servers.server":
                for sheet_title, coordinate in named_range.destinations:
                    if sheet_title == "Servers":
                        server_cell = servers_sheet[coordinate]
                        break

        if not server_cell:
            return None

        # Get servers (horizontally arranged in the sheet)
        servers = []
        col_idx = server_cell.column - 1  # 0-based index
        row_idx = server_cell.row - 1  # 0-based index

        index = 0
        while True:
            server_name = get_cell_value_by_position(servers_sheet, row_idx, col_idx + index)
            if not server_name:
                break

            server = Server(
                server=server_name,
                description=get_server_cell_value(servers_sheet, "servers.description", index),
                environment=get_server_cell_value(servers_sheet, "servers.environment", index),
                type=get_server_cell_value(servers_sheet, "servers.type", index),
                project=None,
                dataset=None,
                location=None,
                delimiter=None,
                endpointUrl=None,
                account=None,
                database=None,
                schema=None,
                warehouse=None,
                table=None,
                view=None,
                catalog=None,
                port=None,
                host=None,
                topic=None,
                path=None,
                format=None,
                stagingDir=None,
                roles=None,
                customProperties=None,
            )

            # Get type-specific fields
            server_type = server.type
            if server_type:
                if server_type == "azure":
                    server.location = get_server_cell_value(servers_sheet, "servers.azure.location", index)
                    server.format = get_server_cell_value(servers_sheet, "servers.azure.format", index)
                    server.delimiter = get_server_cell_value(servers_sheet, "servers.azure.delimiter", index)
                elif server_type == "bigquery":
                    server.project = get_server_cell_value(servers_sheet, "servers.bigquery.project", index)
                    server.dataset = get_server_cell_value(servers_sheet, "servers.bigquery.dataset", index)
                elif server_type == "databricks":
                    server.catalog = get_server_cell_value(servers_sheet, "servers.databricks.catalog", index)
                    server.host = get_server_cell_value(servers_sheet, "servers.databricks.host", index)
                    server.schema = get_server_cell_value(servers_sheet, "servers.databricks.schema", index)
                # Add other server types as needed

            servers.append(server)
            index += 1
    except Exception as e:
        logger.debug(f"Error importing servers: {str(e)}")
        return None

    return servers if servers else None


def get_server_cell_value(sheet, name, col_offset):
    """Get cell value for server properties (arranged horizontally)"""
    try:
        cell = find_cell_by_name(sheet, name)
        if not cell:
            return None

        row = cell.row - 1  # 0-based
        col = cell.column - 1 + col_offset  # 0-based
        return get_cell_value_by_position(sheet, row, col)
    except Exception as e:
        logger.debug(f"Error getting server cell value for {name}: {str(e)}")
        return None


def find_cell_by_name(sheet, name):
    """Find a cell by name within a sheet"""
    try:
        workbook = sheet.parent
        for named_range in workbook.defined_names.definedName:
            if named_range.name == name:
                for sheet_title, coordinate in named_range.destinations:
                    if sheet_title == sheet.title:
                        return sheet[coordinate]
    except Exception as e:
        logger.debug(f"Error finding cell by name {name}: {str(e)}")
    return None


def get_cell_value_by_position(sheet, row_idx, col_idx):
    """Get cell value by row and column indices (0-based)"""
    try:
        cell = sheet.cell(row=row_idx + 1, column=col_idx + 1)  # Convert to 1-based indices
        return str(cell.value) if cell.value is not None else None
    except Exception as e:
        logger.debug(f"Error getting cell value by position ({row_idx}, {col_idx}): {str(e)}")
        return None


def import_price(workbook) -> Optional[Dict[str, Any]]:
    """Extract price information"""
    try:
        price_amount = get_cell_value_by_name(workbook, "price.priceAmount")
        price_currency = get_cell_value_by_name(workbook, "price.priceCurrency")
        price_unit = get_cell_value_by_name(workbook, "price.priceUnit")

        if not (price_amount or price_currency or price_unit):
            return None

        # Create a dictionary for price since the class doesn't seem to be directly available
        return {
            "priceAmount": price_amount,
            "priceCurrency": price_currency,
            "priceUnit": price_unit,
        }
    except Exception as e:
        logger.debug(f"Error importing price: {str(e)}")
        return None


def import_custom_properties(owner, workbook) -> List[CustomProperty]:
    """Extract custom properties"""
    custom_properties = []

    # Add owner as a custom property
    if owner:
        custom_properties.append(
            CustomProperty(
                property="owner",
                value=owner,
            )
        )

    try:
        # Get other custom properties
        custom_properties_sheet = workbook.get("Custom Properties")
        if custom_properties_sheet:
            custom_properties_range = find_range_by_name(custom_properties_sheet, "customProperties")
            if custom_properties_range:
                # Skip header row
                for row_idx in range(custom_properties_range[0], custom_properties_range[1]):
                    if row_idx == custom_properties_range[0] - 1:
                        continue

                    property_name = get_cell_value_by_position(custom_properties_sheet, row_idx, 0)
                    if not property_name or property_name == "owner":
                        continue

                    property_value = get_cell_value_by_position(custom_properties_sheet, row_idx, 1)

                    custom_properties.append(
                        CustomProperty(
                            property=property_name,
                            value=property_value,
                        )
                    )
    except Exception as e:
        logger.debug(f"Error importing custom properties: {str(e)}")

    return custom_properties
