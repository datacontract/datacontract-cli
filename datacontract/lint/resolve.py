import logging

import fastjsonschema
import yaml
from fastjsonschema import JsonSchemaValueException

from datacontract.lint.files import read_file
from datacontract.lint.schema import fetch_schema
from datacontract.lint.urls import fetch_resource
from datacontract.model.data_contract_specification import \
    DataContractSpecification, Definition
from datacontract.model.exceptions import DataContractException


def resolve_data_contract(
    data_contract_location: str = None,
    data_contract_str: str = None,
    data_contract: DataContractSpecification = None,
    schema_location: str = None,
    inline_definitions: bool = False
) -> DataContractSpecification:
    if data_contract_location is not None:
        return resolve_data_contract_from_location(data_contract_location, schema_location, inline_definitions)
    elif data_contract_str is not None:
        return resolve_data_contract_from_str(data_contract_str, schema_location, inline_definitions)
    elif data_contract is not None:
        return data_contract
    else:
        raise DataContractException(
            type="lint",
            result="failed",
            name="Check that data contract YAML is valid",
            reason=f"Data contract needs to be provided",
            engine="datacontract",
        )


def resolve_data_contract_from_location(
    location, schema_location: str = None,
    inline_definitions: bool = False
) -> DataContractSpecification:
    if location.startswith("http://") or location.startswith("https://"):
        data_contract_str = fetch_resource(location)
    else:
        data_contract_str = read_file(location)
    return resolve_data_contract_from_str(data_contract_str, schema_location, inline_definitions)


def inline_definitions_into_data_contract(spec: DataContractSpecification):
    for model in spec.models.values():
        for field in model.fields.values():
            if field.ref is None:
                continue

            definition = resolve_ref(field.ref, spec.definitions)
            field.ref_obj = definition

            for field_name in field.model_fields.keys():
                if (field_name in definition.model_fields_set and
                    field_name not in field.model_fields_set):
                    setattr(field, field_name,
                            getattr(definition, field_name))

def resolve_ref(ref, definitions) -> Definition:
    if ref.startswith("http://") or ref.startswith("https://"):
        definition_str = fetch_resource(ref)
        definition_dict = to_yaml(definition_str)
        return Definition(**definition_dict)

    elif ref.startswith("#/definitions/"):
        definition_name = ref.split("#/definitions/")[1]
        return definitions[definition_name]
    else:
        raise DataContractException(
            type="lint",
            result="failed",
            name="Check that data contract YAML is valid",
            reason=f"Cannot resolve reference {ref}",
            engine="datacontract",
        )


def resolve_data_contract_from_str(
    data_contract_str, schema_location: str = None,
    inline_definitions: bool = False
) -> DataContractSpecification:
    data_contract_yaml_dict = to_yaml(data_contract_str)
    validate(data_contract_yaml_dict, schema_location)

    spec = DataContractSpecification(**data_contract_yaml_dict)

    if inline_definitions:
        inline_definitions_into_data_contract(spec)

    return spec


def to_yaml(data_contract_str):
    try:
        yaml_dict = yaml.safe_load(data_contract_str)
        return yaml_dict
    except Exception as e:
        logging.warning(f"Cannot parse YAML. Error: {str(e)}")
        raise DataContractException(
            type="lint",
            result="failed",
            name="Check that data contract YAML is valid",
            reason=f"Cannot parse YAML. Error: {str(e)}",
            engine="datacontract",
        )


def validate(data_contract_yaml, schema_location: str = None):
    schema = fetch_schema(schema_location)
    try:
        fastjsonschema.validate(schema, data_contract_yaml)
        logging.debug("YAML data is valid.")
    except JsonSchemaValueException as e:
        logging.warning(f"Data Contract YAML is invalid. Validation error: {e.message}")
        raise DataContractException(
            type="lint",
            result="failed",
            name="Check that data contract YAML is valid",
            reason=e.message,
            engine="datacontract",
        )
    except Exception as e:
        logging.warning(f"Data Contract YAML is invalid. Validation error: {str(e)}")
        raise DataContractException(
            type="lint",
            result="failed",
            name="Check that data contract YAML is valid",
            reason=str(e),
            engine="datacontract",
        )
