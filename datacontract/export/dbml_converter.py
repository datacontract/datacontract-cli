from datetime import datetime
from importlib.metadata import version
import pytz
import datacontract.model.data_contract_specification as spec
from typing import Tuple


def to_dbml_diagram(contract: spec.DataContractSpecification) -> str:
    result = ''
    result += add_generated_info(contract) + "\n"
    result += generate_project_info(contract) + "\n"

    for model_name, model in contract.models.items():
        table_description = generate_table(model_name, model)
        result += f"\n{table_description}\n"

    return result

def add_generated_info(contract: spec.DataContractSpecification) -> str:
    tz = pytz.timezone("UTC")
    now = datetime.now(tz)
    formatted_date = now.strftime("%d %b %Y %H:%M:%S UTC")
    datacontract_cli_version = get_version()

    generated_info = (
        f'Generated at {formatted_date} by datacontract-cli version {datacontract_cli_version}\n'
        f'for datacontract {contract.info.title} ({contract.id}) version {contract.info.version} \n'
    )

    comment = (
        f'/*\n'
        f'{generated_info}\n'
        f'*/\n'
    )

    note = (
        "Note project_info {\n"
        "'''\n"
        f'{generated_info}\n'
        "'''\n"
        "}\n"
    )

    return (
        f"{comment}\n"
        f"{note}"
    )

def get_version() -> str:
    try:
        return version("datacontract_cli")
    except Exception as e:
        return ""

def generate_project_info(contract: spec.DataContractSpecification) -> str:
    return (f'Project "{contract.info.title}" {{ \n'
        f'Note: "{' '.join(contract.info.description.splitlines())}"\n'
    "} \n")

def generate_table(model_name: str, model: spec.Model) -> str:
    result = (
        f'Table "{model_name}" {{ \n'
        f'Note: "{' '.join(model.description.splitlines())}"\n'
    )

    references = []

    # Add all the fields
    for field_name, field in model.fields.items():
        ref, field_string = generate_field(field_name, field, model_name)
        if ref is not None:
            references.append(ref)
        result += f"{field_string}\n"

    result += "}\n"

    # and if any: add the references
    if len(references) > 0:
        for ref in references:
            result += f"Ref: {ref}\n"
        
        result += "\n"

    return result

def generate_field(field_name: str, field: spec.Field, model_name: str) -> Tuple[str, str]:

    field_attrs = []
    if field.primary:
        field_attrs.append('pk')

    if field.unique:
        field_attrs.append('unique')
    
    if field.required:
        field_attrs.append('not null')
    else:
        field_attrs.append('null')

    if field.description:
        field_attrs.append(f'Note: "{' '.join(field.description.splitlines())}"')

    field_str = f'"{field_name}" {field.type} [{','.join(field_attrs)}]'
    ref_str = None
    if (field.references) is not None:
        # we always assume many to one, as datacontract doesn't really give us more info
        ref_str = f"{model_name}.{field_name} > {field.references}"
    return (ref_str, field_str)
