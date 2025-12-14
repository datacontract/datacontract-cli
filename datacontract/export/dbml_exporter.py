from datetime import datetime
from importlib.metadata import version
from typing import Optional, Tuple

import pytz
from open_data_contract_standard.model import OpenDataContractStandard, SchemaObject, SchemaProperty, Server

from datacontract.export.exporter import Exporter
from datacontract.export.sql_type_converter import convert_to_sql_type
from datacontract.model.exceptions import DataContractException


class DbmlExporter(Exporter):
    def export(self, data_contract, schema_name, server, sql_server_type, export_args) -> dict:
        found_server = _get_server_by_name(data_contract, server) if server else None
        return to_dbml_diagram(data_contract, found_server)


def _get_server_by_name(data_contract: OpenDataContractStandard, name: str) -> Optional[Server]:
    """Get a server by name."""
    if data_contract.servers is None:
        return None
    return next((s for s in data_contract.servers if s.server == name), None)


def _get_type(prop: SchemaProperty) -> Optional[str]:
    """Get the type from a schema property."""
    if prop.logicalType:
        return prop.logicalType
    if prop.physicalType:
        return prop.physicalType
    return None


def _get_references(prop: SchemaProperty) -> Optional[str]:
    """Get references from a property's relationships."""
    if prop.relationships:
        for rel in prop.relationships:
            if hasattr(rel, 'to') and rel.to:
                return rel.to
    return None


def to_dbml_diagram(contract: OpenDataContractStandard, server: Optional[Server]) -> str:
    result = ""
    result += add_generated_info(contract, server) + "\n"
    result += generate_project_info(contract) + "\n"

    if contract.schema_:
        for schema_obj in contract.schema_:
            table_description = generate_table(schema_obj.name, schema_obj, server)
            result += f"\n{table_description}\n"

    return result


def add_generated_info(contract: OpenDataContractStandard, server: Optional[Server]) -> str:
    tz = pytz.timezone("UTC")
    now = datetime.now(tz)
    formatted_date = now.strftime("%b %d %Y")
    datacontract_cli_version = get_version()
    dialect = "Logical Datacontract" if server is None else server.type

    return """/*
Generated at {0} by datacontract-cli version {1}
for datacontract {2} ({3}) version {4}
Using {5} Types for the field types
*/""".format(
        formatted_date, datacontract_cli_version, contract.name, contract.id, contract.version, dialect
    )


def get_version() -> str:
    try:
        return version("datacontract_cli")
    except Exception:
        return ""


def generate_project_info(contract: OpenDataContractStandard) -> str:
    description = ""
    if contract.description:
        if hasattr(contract.description, 'purpose') and contract.description.purpose:
            description = contract.description.purpose
        elif isinstance(contract.description, str):
            description = contract.description
    return """Project "{0}" {{
    note: '''{1}'''
}}""".format(contract.name or "", description)


def generate_table(model_name: str, schema_obj: SchemaObject, server: Optional[Server]) -> str:
    result = "Table {0} {{\n    note: {1}\n".format(model_name, formatDescription(schema_obj.description or ""))

    references = []

    if schema_obj.properties:
        for prop in schema_obj.properties:
            ref, field_string = generate_field(prop.name, prop, model_name, server)
            if ref is not None:
                references.append(ref)
            result += "{0}\n".format(field_string)

    result += "}"

    # and if any: add the references
    if len(references) > 0:
        result += "\n"
        for ref in references:
            result += "Ref: {0}\n".format(ref)

    return result


def generate_field(field_name: str, prop: SchemaProperty, model_name: str, server: Optional[Server]) -> Tuple[str, str]:
    if prop.primaryKey:
        if prop.required is not None:
            if not prop.required:
                raise DataContractException(
                    type="lint",
                    name="Primary key fields cannot have required == False.",
                    result="error",
                    reason="Primary key fields cannot have required == False.",
                    engine="datacontract",
                )
        else:
            prop.required = True
        if prop.unique is not None:
            if not prop.unique:
                raise DataContractException(
                    type="lint",
                    name="Primary key fields cannot have unique == False",
                    result="error",
                    reason="Primary key fields cannot have unique == False.",
                    engine="datacontract",
                )
        else:
            prop.unique = True

    field_attrs = []
    if prop.primaryKey:
        field_attrs.append("pk")

    if prop.unique:
        field_attrs.append("unique")

    if prop.required:
        field_attrs.append("not null")
    else:
        field_attrs.append("null")

    if prop.description:
        field_attrs.append("""note: {0}""".format(formatDescription(prop.description)))

    prop_type = _get_type(prop)
    field_type = prop_type if server is None else convert_to_sql_type(prop, server.type)

    field_str = '    {0} {1} [{2}]'.format(field_name, field_type, ", ".join(field_attrs))
    ref_str = None
    references = _get_references(prop)
    if references is not None:
        if prop.unique:
            ref_str = "{0}.{1} - {2}".format(model_name, field_name, references)
        else:
            ref_str = "{0}.{1} > {2}".format(model_name, field_name, references)
    return (ref_str, field_str)


def formatDescription(input: str) -> str:
    if "\n" in input or "\r" in input or '"' in input:
        return "'''{0}'''".format(input)
    else:
        return '"{0}"'.format(input)
