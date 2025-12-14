from typing import Dict, List, Optional

from open_data_contract_standard.model import (
    Description,
    OpenDataContractStandard,
    SchemaObject,
    SchemaProperty,
    Server,
    ServiceLevelAgreementProperty,
)
from pydantic import BaseModel

from datacontract.export.exporter import Exporter

TAB = "&#x2007;"
ARROW = "&#x21b3;"


class MarkdownExporter(Exporter):
    """Exporter implementation for converting data contracts to Markdown."""

    def export(
        self,
        data_contract: OpenDataContractStandard,
        schema_name: str,
        server: str,
        sql_server_type: str,
        export_args: dict,
    ) -> str:
        """Exports a data contract to Markdown format."""
        return to_markdown(data_contract)


def to_markdown(data_contract: OpenDataContractStandard) -> str:
    """
    Convert a data contract to its Markdown representation.

    Args:
        data_contract (OpenDataContractStandard): The data contract to convert.

    Returns:
        str: The Markdown representation of the data contract.
    """
    markdown_parts = [
        f"# {data_contract.id}",
        "## Info",
        info_to_markdown(data_contract),
        "",
        "## Terms of Use",
        terms_of_use_to_markdown(data_contract.description),
        "",
        "## Servers",
        servers_to_markdown(data_contract.servers),
        "",
        "## Schema",
        schema_to_markdown(data_contract.schema_),
        "",
        "## SLA Properties",
        sla_properties_to_markdown(data_contract.slaProperties),
    ]
    return "\n".join(markdown_parts)


def info_to_markdown(data_contract: OpenDataContractStandard) -> str:
    """Convert basic info to markdown."""
    parts = []
    if data_contract.description:
        parts.append(f"*{description_to_markdown(data_contract.description)}*")
    if data_contract.name:
        parts.append(f"- **name:** {data_contract.name}")
    if data_contract.version:
        parts.append(f"- **version:** {data_contract.version}")
    if data_contract.status:
        parts.append(f"- **status:** {data_contract.status}")
    if data_contract.team:
        parts.append(f"- **team:** {data_contract.team.name}")
    return "\n".join(parts)


def terms_of_use_to_markdown(description: Optional[Description]) -> str:
    """Convert Description object's terms of use fields to markdown."""
    if not description:
        return "*No terms of use defined.*"

    # Handle case where description is a string (legacy)
    if isinstance(description, str):
        return "*No terms of use defined.*"

    parts = []
    if description.usage:
        parts.append(f"### Usage\n{description.usage}")
    if description.purpose:
        parts.append(f"### Purpose\n{description.purpose}")
    if description.limitations:
        parts.append(f"### Limitations\n{description.limitations}")

    if not parts:
        return "*No terms of use defined.*"

    return "\n\n".join(parts)


def obj_attributes_to_markdown(obj: BaseModel, excluded_fields: set = set(), is_in_table_cell: bool = False) -> str:
    if not obj:
        return ""
    if is_in_table_cell:
        bullet_char = "•"
        newline_char = "<br>"
    else:
        bullet_char = "-"
        newline_char = "\n"
    model_attributes_to_include = set(obj.__class__.model_fields.keys())
    obj_model = obj.model_dump(exclude_unset=True, include=model_attributes_to_include, exclude=excluded_fields)
    description_value = obj_model.pop("description", None)
    attributes = [
        (f"{bullet_char} `{attr}`" if value is True else f"{bullet_char} **{attr}:** {value}")
        for attr, value in obj_model.items()
        if value
    ]
    description = f"*{description_to_markdown(description_value)}*"
    extra = [extra_to_markdown(obj, is_in_table_cell)] if obj.model_extra else []
    return newline_char.join([description] + attributes + extra)


def servers_to_markdown(servers: Optional[List[Server]]) -> str:
    if not servers:
        return ""
    markdown_parts = [
        "| Name | Type | Attributes |",
        "| ---- | ---- | ---------- |",
    ]
    for server in servers:
        server_name = server.server or ""
        markdown_parts.append(
            f"| {server_name} | {server.type or ''} | {obj_attributes_to_markdown(server, {'type', 'server'}, True)} |"
        )
    return "\n".join(markdown_parts)


def schema_to_markdown(schema: Optional[List[SchemaObject]]) -> str:
    if not schema:
        return ""
    return "\n".join(schema_obj_to_markdown(schema_obj.name, schema_obj) for schema_obj in schema)


def schema_obj_to_markdown(model_name: str, schema_obj: SchemaObject) -> str:
    """
    Generate Markdown representation for a specific schema object.

    Args:
        model_name (str): The name of the model.
        schema_obj (SchemaObject): The schema object.

    Returns:
        str: The Markdown representation of the schema object.
    """
    parts = [
        f"### {model_name}",
        f"*{description_to_markdown(schema_obj.description)}*",
        "",
        "| Field | Type | Attributes |",
        "| ----- | ---- | ---------- |",
    ]

    # Append generated field rows
    parts.append(properties_to_markdown(schema_obj.properties))
    return "\n".join(parts)


def properties_to_markdown(
    properties: Optional[List[SchemaProperty]],
    level: int = 0,
) -> str:
    """
    Generate Markdown table rows for all properties in a schema.

    Args:
        properties (List[SchemaProperty]): The properties to process.
        level (int): The level of nesting for indentation.

    Returns:
        str: A Markdown table rows for the properties.
    """
    if not properties:
        return ""
    return "\n".join(property_to_markdown(prop.name, prop, level) for prop in properties)


def _get_type(prop: SchemaProperty) -> str:
    """Get the display type for a property."""
    if prop.logicalType:
        return prop.logicalType
    if prop.physicalType:
        return prop.physicalType
    return ""


def property_to_markdown(field_name: str, prop: SchemaProperty, level: int = 0) -> str:
    """
    Generate Markdown table rows for a single property, including nested structures.

    Args:
        field_name (str): The name of the field.
        prop (SchemaProperty): The property object.
        level (int): The level of nesting for indentation.

    Returns:
        str: A Markdown table rows for the property.
    """
    tabs = TAB * level
    arrow = ARROW if level > 0 else ""
    column_name = f"{tabs}{arrow} {field_name}"

    prop_type = _get_type(prop)
    attributes = obj_attributes_to_markdown(prop, {"name", "logicalType", "physicalType", "properties", "items"}, True)

    rows = [f"| {column_name} | {prop_type} | {attributes} |"]

    # Recursively handle nested properties, array
    if prop.properties:
        rows.append(properties_to_markdown(prop.properties, level + 1))
    if prop.items:
        rows.append(property_to_markdown("items", prop.items, level + 1))

    return "\n".join(rows)


def sla_properties_to_markdown(sla_properties: Optional[List[ServiceLevelAgreementProperty]]) -> str:
    """Convert SLA properties to markdown."""
    if not sla_properties:
        return ""

    markdown_parts = [
        "| Property | Value | Unit |",
        "| -------- | ----- | ---- |",
    ]
    for sla in sla_properties:
        prop_name = sla.property or ""
        value = sla.value or ""
        unit = sla.unit or ""
        markdown_parts.append(f"| {prop_name} | {value} | {unit} |")
    return "\n".join(markdown_parts)


def description_to_markdown(description) -> str:
    """Convert a description (string or Description object) to markdown text."""
    if description is None:
        return "No description."
    if isinstance(description, str):
        return description.replace("\n", "<br>")
    # Handle Description object - use purpose as the primary description
    if hasattr(description, "purpose") and description.purpose:
        return description.purpose.replace("\n", "<br>")
    if hasattr(description, "usage") and description.usage:
        return description.usage.replace("\n", "<br>")
    return "No description."


def array_of_dict_to_markdown(array: List[Dict[str, str]]) -> str:
    """
    Convert a list of dictionaries to a Markdown table.

    Args:
        array (List[Dict[str, str]]): A list of dictionaries where each dictionary represents a row in the table.

    Returns:
        str: A Markdown formatted table.
    """
    if not array:
        return ""

    headers = []

    for item in array:
        headers += item.keys()
    headers = list(dict.fromkeys(headers))  # Preserve order and remove duplicates

    markdown_parts = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]

    for row in array:
        element = row
        markdown_parts.append(
            "| "
            + " | ".join(
                f"{str(element.get(header, ''))}".replace("\n", "<br>").replace("\t", TAB) for header in headers
            )
            + " |"
        )

    return "\n".join(markdown_parts) + "\n"


def array_to_markdown(array: List[str]) -> str:
    """
    Convert a list of strings to a Markdown formatted list.

    Args:
        array (List[str]): A list of strings to convert.

    Returns:
        str: A Markdown formatted list.
    """
    if not array:
        return ""
    return "\n".join(f"- {item}" for item in array) + "\n"


def dict_to_markdown(dictionary: Dict[str, str]) -> str:
    """
    Convert a dictionary to a Markdown formatted list.

    Args:
        dictionary (Dict[str, str]): A dictionary where keys are item names and values are item descriptions.

    Returns:
        str: A Markdown formatted list of items.
    """
    if not dictionary:
        return ""

    markdown_parts = []
    for key, value in dictionary.items():
        if isinstance(value, dict):
            markdown_parts.append(f"- {key}")
            nested_markdown = dict_to_markdown(value)
            if nested_markdown:
                nested_lines = nested_markdown.split("\n")
                for line in nested_lines:
                    if line.strip():
                        markdown_parts.append(f"  {line}")
        else:
            markdown_parts.append(f"- {key}: {value}")
    return "\n".join(markdown_parts) + "\n"


def extra_to_markdown(obj: BaseModel, is_in_table_cell: bool = False) -> str:
    """
    Convert the extra attributes of a data contract to Markdown format.
    Args:
        obj (BaseModel): The data contract object containing extra attributes.
        is_in_table_cell (bool): Whether the extra attributes are in a table cell.
    Returns:
        str: A Markdown formatted string representing the extra attributes of the data contract.
    """
    extra = obj.model_extra

    if not extra:
        return ""

    bullet_char = "•"
    value_line_ending = "" if is_in_table_cell else "\n"
    row_suffix = "<br>" if is_in_table_cell else ""

    def render_header(key: str) -> str:
        return f"{bullet_char} **{key}:** " if is_in_table_cell else f"\n### {key.capitalize()}\n"

    parts: list[str] = []
    for key_extra, value_extra in extra.items():
        if not value_extra:
            continue

        parts.append(render_header(key_extra))

        if isinstance(value_extra, list) and len(value_extra):
            if isinstance(value_extra[0], dict):
                parts.append(array_of_dict_to_markdown(value_extra))
            elif isinstance(value_extra[0], str):
                parts.append(array_to_markdown(value_extra))
        elif isinstance(value_extra, dict):
            parts.append(dict_to_markdown(value_extra))
        else:
            parts.append(f"{str(value_extra)}{value_line_ending}")

        if row_suffix:
            parts.append(row_suffix)

    return "".join(parts)
