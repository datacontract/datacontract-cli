from datetime import datetime
from importlib.metadata import version
from typing import Tuple

import pytz

import datacontract.model.data_contract_specification as spec
from datacontract.export.exporter import Exporter
from datacontract.export.sql_type_converter import convert_to_sql_type
from datacontract.model.exceptions import DataContractException


class DbmlExporter(Exporter):
    def export(self, data_contract, model, server, sql_server_type, export_args) -> dict:
        found_server = data_contract.servers.get(server)
        return to_dbml_diagram(data_contract, found_server)


def to_dbml_diagram(contract: spec.DataContractSpecification, server: spec.Server) -> str:
    result = ""
    result += add_generated_info(contract, server) + "\n"
    result += generate_project_info(contract) + "\n"

    for model_name, model in contract.models.items():
        table_description = generate_table(model_name, model, server)
        result += f"\n{table_description}\n"

    return result


def add_generated_info(contract: spec.DataContractSpecification, server: spec.Server) -> str:
    tz = pytz.timezone("UTC")
    now = datetime.now(tz)
    formatted_date = now.strftime("%b %d %Y")
    datacontract_cli_version = get_version()
    dialect = "Logical Datacontract" if server is None else server.type

    generated_info = """
Generated at {0} by datacontract-cli version {1}
for datacontract {2} ({3}) version {4} 
Using {5} Types for the field types
    """.format(
        formatted_date, datacontract_cli_version, contract.info.title, contract.id, contract.info.version, dialect
    )

    comment = """/*
{0}
*/
    """.format(generated_info)
    return comment


def get_version() -> str:
    try:
        return version("datacontract_cli")
    except Exception:
        return ""


def generate_project_info(contract: spec.DataContractSpecification) -> str:
    return """Project "{0}" {{
    Note: '''{1}'''
}}\n
    """.format(contract.info.title, contract.info.description)


def generate_table(model_name: str, model: spec.Model, server: spec.Server) -> str:
    result = """Table "{0}" {{ 
Note: {1}
    """.format(model_name, formatDescription(model.description))

    references = []

    for field_name, field in model.fields.items():
        ref, field_string = generate_field(field_name, field, model_name, server)
        if ref is not None:
            references.append(ref)
        result += "{0}\n".format(field_string)

    result += "}\n"

    # and if any: add the references
    if len(references) > 0:
        for ref in references:
            result += "Ref: {0}\n".format(ref)

        result += "\n"

    return result


def generate_field(field_name: str, field: spec.Field, model_name: str, server: spec.Server) -> Tuple[str, str]:
    if field.primaryKey or field.primary:
        if field.required is not None:
            if not field.required:
                raise DataContractException(
                    type="lint",
                    name="Primary key fields cannot have required == False.",
                    result="error",
                    reason="Primary key fields cannot have required == False.",
                    engine="datacontract",
                )
        else:
            field.required = True
        if field.unique is not None:
            if not field.unique:
                raise DataContractException(
                    type="lint",
                    name="Primary key fields cannot have unique == False",
                    result="error",
                    reason="Primary key fields cannot have unique == False.",
                    engine="datacontract",
                )
        else:
            field.unique = True

    field_attrs = []
    if field.primaryKey or field.primary:
        field_attrs.append("pk")

    if field.unique:
        field_attrs.append("unique")

    if field.required:
        field_attrs.append("not null")
    else:
        field_attrs.append("null")

    if field.description:
        field_attrs.append("""Note: {0}""".format(formatDescription(field.description)))

    field_type = field.type if server is None else convert_to_sql_type(field, server.type)

    field_str = '"{0}" "{1}" [{2}]'.format(field_name, field_type, ",".join(field_attrs))
    ref_str = None
    if (field.references) is not None:
        if field.unique:
            ref_str = "{0}.{1} - {2}".format(model_name, field_name, field.references)
        else:
            ref_str = "{0}.{1} > {2}".format(model_name, field_name, field.references)
    return (ref_str, field_str)


def formatDescription(input: str) -> str:
    if "\n" in input or "\r" in input or '"' in input:
        return "'''{0}'''".format(input)
    else:
        return '"{0}"'.format(input)
