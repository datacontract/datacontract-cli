import logging
import os

import fastjsonschema
import yaml
from fastjsonschema import JsonSchemaValueException

from datacontract.lint.files import read_file
from datacontract.lint.schema import fetch_schema
from datacontract.lint.urls import fetch_resource
from datacontract.model.data_contract_specification import DataContractSpecification, Definition, Quality
from datacontract.model.exceptions import DataContractException


def resolve_data_contract(
    data_contract_location: str = None,
    data_contract_str: str = None,
    data_contract: DataContractSpecification = None,
    schema_location: str = None,
    inline_definitions: bool = False,
    inline_quality: bool = False,
) -> DataContractSpecification:
    if data_contract_location is not None:
        return resolve_data_contract_from_location(
            data_contract_location, schema_location, inline_definitions, inline_quality
        )
    elif data_contract_str is not None:
        return _resolve_data_contract_from_str(data_contract_str, schema_location, inline_definitions, inline_quality)
    elif data_contract is not None:
        return data_contract
    else:
        raise DataContractException(
            type="lint",
            result="failed",
            name="Check that data contract YAML is valid",
            reason="Data contract needs to be provided",
            engine="datacontract",
        )


def resolve_data_contract_from_location(
    location, schema_location: str = None, inline_definitions: bool = False, inline_quality: bool = False
) -> DataContractSpecification:
    if location.startswith("http://") or location.startswith("https://"):
        data_contract_str = fetch_resource(location)
    else:
        data_contract_str = read_file(location)
    return _resolve_data_contract_from_str(data_contract_str, schema_location, inline_definitions, inline_quality)


def inline_definitions_into_data_contract(spec: DataContractSpecification):
    for model in spec.models.values():
        for field in model.fields.values():
            # If ref_obj is not empty, we've already inlined definitions.
            if not field.ref and not field.ref_obj:
                continue

            definition = _resolve_definition_ref(field.ref, spec)
            field.ref_obj = definition

            for field_name in field.model_fields.keys():
                if field_name in definition.model_fields_set and field_name not in field.model_fields_set:
                    setattr(field, field_name, getattr(definition, field_name))
            # extras
            for extra_field_name, extra_field_value in definition.model_extra.items():
                if extra_field_name not in field.model_extra.keys():
                    setattr(field, extra_field_name, extra_field_value)


def _resolve_definition_ref(ref, spec) -> Definition:
    logging.info(f"Resolving definition ref {ref}")

    if "#" in ref:
        path, definition_path = ref.split("#")
    else:
        path, definition_path = ref, None

    if path.startswith("http://") or path.startswith("https://"):
        logging.info(f"Resolving definition url {path}")

        definition_str = fetch_resource(path)
        definition_dict = _to_yaml(definition_str)
        definition = Definition(**definition_dict)
        if definition_path is not None:
            return _find_by_path_in_definition(definition_path, definition)
        else:
            return definition
    elif path.startswith("file://"):
        logging.info(f"Resolving definition file path {path}")

        path = path.replace("file://", "")
        definition_str = _fetch_file(path)
        definition_dict = _to_yaml(definition_str)
        definition = Definition(**definition_dict)
        if definition_path is not None:
            return _find_by_path_in_definition(definition_path, definition)
        else:
            return definition
    elif ref.startswith("#"):
        logging.info(f"Resolving definition local path {path}")

        definition_path = ref[1:]

        return _find_by_path_in_spec(definition_path, spec)
    else:
        raise DataContractException(
            type="lint",
            result="failed",
            name="Check that data contract YAML is valid",
            reason=f"Cannot resolve reference {ref}",
            engine="datacontract",
        )


def _find_by_path_in_spec(definition_path: str, spec: DataContractSpecification):
    path_elements = definition_path.split("/")
    definition_key = path_elements[2]
    if definition_key not in spec.definitions:
        raise DataContractException(
            type="lint",
            result="failed",
            name="Check that data contract YAML is valid",
            reason=f"Cannot resolve definition {definition_key}",
            engine="datacontract",
        )
    definition = spec.definitions[definition_key]
    definition = _find_subfield_in_definition(definition, path_elements[3:])
    return definition


def _find_by_path_in_definition(definition_path: str, definition: Definition):
    if definition_path == "" or definition_path == "/":
        return definition

    path_elements = definition_path.split("/")
    return _find_subfield_in_definition(definition, path_elements[1:])


def _find_subfield_in_definition(definition: Definition, path_elements):
    while len(path_elements) > 0 and path_elements[0] == "fields":
        definition = definition.fields[path_elements[1]]
        path_elements = path_elements[2:]

    return definition


def _fetch_file(path) -> str:
    if not os.path.exists(path):
        raise DataContractException(
            type="export",
            result="failed",
            name="Check that data contract definition is valid",
            reason=f"Cannot resolve reference {path}",
            engine="datacontract",
        )
    with open(path, "r") as file:
        return file.read()


def _resolve_quality_ref(quality: Quality):
    """
    Return the content of a ref file path
    @param quality data contract quality specification
    """
    if isinstance(quality.specification, dict):
        specification = quality.specification
        if quality.type == "great-expectations":
            for model, model_quality in specification.items():
                specification[model] = _get_quality_ref_file(model_quality)
        else:
            if "$ref" in specification:
                quality.specification = _get_quality_ref_file(specification)


def _get_quality_ref_file(quality_spec: str | object) -> str | object:
    """
    Get the file associated with a quality reference
    @param quality_spec quality specification
    @returns: the content of the quality file
    """
    if isinstance(quality_spec, dict) and "$ref" in quality_spec:
        ref = quality_spec["$ref"]
        if not os.path.exists(ref):
            raise DataContractException(
                type="export",
                result="failed",
                name="Check that data contract quality is valid",
                reason=f"Cannot resolve reference {ref}",
                engine="datacontract",
            )
        with open(ref, "r") as file:
            quality_spec = file.read()
    return quality_spec


def _resolve_data_contract_from_str(
    data_contract_str, schema_location: str = None, inline_definitions: bool = False, inline_quality: bool = False
) -> DataContractSpecification:
    data_contract_yaml_dict = _to_yaml(data_contract_str)
    _validate(data_contract_yaml_dict, schema_location)

    spec = DataContractSpecification(**data_contract_yaml_dict)

    if inline_definitions:
        inline_definitions_into_data_contract(spec)
    if spec.quality and inline_quality:
        _resolve_quality_ref(spec.quality)

    return spec


def _to_yaml(data_contract_str):
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


def _validate(data_contract_yaml, schema_location: str = None):
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
