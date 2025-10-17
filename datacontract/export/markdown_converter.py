from typing import Dict, List

from pydantic import BaseModel

from datacontract.export.exporter import Exporter
from datacontract.model.data_contract_specification import (
    DataContractSpecification,
    Definition,
    Field,
    Model,
    Server,
    ServiceLevel,
)

TAB = "&#x2007;"
ARROW = "&#x21b3;"


class MarkdownExporter(Exporter):
    """Exporter implementation for converting data contracts to Markdown."""

    def export(
        self,
        data_contract: DataContractSpecification,
        model: Model,
        server: str,
        sql_server_type: str,
        export_args: dict,
    ) -> str:
        """Exports a data contract to Markdown format."""
        return to_markdown(data_contract)


def to_markdown(data_contract: DataContractSpecification) -> str:
    """
    Convert a data contract to its Markdown representation.

    Args:
        data_contract (DataContractSpecification): The data contract to convert.

    Returns:
        str: The Markdown representation of the data contract.
    """
    markdown_parts = [
        f"# {data_contract.id}",
        "## Info",
        obj_attributes_to_markdown(data_contract.info),
        "",
        "## Servers",
        servers_to_markdown(data_contract.servers),
        "",
        "## Terms",
        obj_attributes_to_markdown(data_contract.terms),
        "",
        "## Models",
        models_to_markdown(data_contract.models),
        "",
        "## Definitions",
        definitions_to_markdown(data_contract.definitions),
        "",
        "## Service levels",
        service_level_to_markdown(data_contract.servicelevels),
    ]
    return "\n".join(markdown_parts)


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


def servers_to_markdown(servers: Dict[str, Server]) -> str:
    if not servers:
        return ""
    markdown_parts = [
        "| Name | Type | Attributes |",
        "| ---- | ---- | ---------- |",
    ]
    for server_name, server in servers.items():
        markdown_parts.append(
            f"| {server_name} | {server.type or ''} | {obj_attributes_to_markdown(server, {'type'}, True)} |"
        )
    return "\n".join(markdown_parts)


def models_to_markdown(models: Dict[str, Model]) -> str:
    return "\n".join(model_to_markdown(model_name, model) for model_name, model in models.items())


def model_to_markdown(model_name: str, model: Model) -> str:
    """
    Generate Markdown representation for a specific model.

    Args:
        model_name (str): The name of the model.
        model (Model): The model object.

    Returns:
        str: The Markdown representation of the model.
    """
    parts = [
        f"### {model_name}",
        f"*{description_to_markdown(model.description)}*",
        "",
        "| Field | Type | Attributes |",
        "| ----- | ---- | ---------- |",
    ]

    # Append generated field rows
    parts.append(fields_to_markdown(model.fields))
    return "\n".join(parts)


def fields_to_markdown(
    fields: Dict[str, Field],
    level: int = 0,
) -> str:
    """
    Generate Markdown table rows for all fields in a model.

    Args:
        fields (Dict[str, Field]): The fields to process.
        level (int): The level of nesting for indentation.

    Returns:
        str: A Markdown table rows for the fields.
    """

    return "\n".join(field_to_markdown(field_name, field, level) for field_name, field in fields.items())


def field_to_markdown(field_name: str, field: Field, level: int = 0) -> str:
    """
    Generate Markdown table rows for a single field, including nested structures.

    Args:
        field_name (str): The name of the field.
        field (Field): The field object.
        level (int): The level of nesting for indentation.

    Returns:
        str: A Markdown table rows for the field.
    """
    tabs = TAB * level
    arrow = ARROW if level > 0 else ""
    column_name = f"{tabs}{arrow} {field_name}"

    attributes = obj_attributes_to_markdown(field, {"type", "fields", "items", "keys", "values"}, True)

    rows = [f"| {column_name} | {field.type} | {attributes} |"]

    # Recursively handle nested fields, array, map
    if field.fields:
        rows.append(fields_to_markdown(field.fields, level + 1))
    if field.items:
        rows.append(field_to_markdown("items", field.items, level + 1))
    if field.keys:
        rows.append(field_to_markdown("keys", field.keys, level + 1))
    if field.values:
        rows.append(field_to_markdown("values", field.values, level + 1))

    return "\n".join(rows)


def definitions_to_markdown(definitions: Dict[str, Definition]) -> str:
    if not definitions:
        return ""
    markdown_parts = [
        "| Name | Type | Domain | Attributes |",
        "| ---- | ---- | ------ | ---------- |",
    ]
    for definition_name, definition in definitions.items():
        markdown_parts.append(
            f"| {definition_name} | {definition.type or ''} | {definition.domain or ''} | {obj_attributes_to_markdown(definition, {'name', 'type', 'domain'}, True)} |",
        )
    return "\n".join(markdown_parts)


def service_level_to_markdown(service_level: ServiceLevel | None) -> str:
    if not service_level:
        return ""
    sections = {
        "Availability": service_level.availability,
        "Retention": service_level.retention,
        "Latency": service_level.latency,
        "Freshness": service_level.freshness,
        "Frequency": service_level.frequency,
        "Support": service_level.support,
        "Backup": service_level.backup,
    }
    result = [f"### {name}\n{obj_attributes_to_markdown(attr)}\n" for name, attr in sections.items() if attr]
    return "\n".join(result)


def description_to_markdown(description: str | None) -> str:
    return (description or "No description.").replace("\n", "<br>")


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
