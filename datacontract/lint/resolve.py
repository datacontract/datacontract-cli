import importlib.resources as resources
import logging
from pathlib import Path

import fastjsonschema
import yaml
from fastjsonschema import JsonSchemaValueException
from open_data_contract_standard.model import OpenDataContractStandard, SchemaProperty

from datacontract.lint.resources import read_resource
from datacontract.lint.schema import fetch_schema
from datacontract.model.exceptions import DataContractException
from datacontract.model.odcs import is_open_data_contract_standard, is_open_data_product_standard
from datacontract.model.run import ResultEnum


class _SafeLoaderNoTimestamp(yaml.SafeLoader):
    """SafeLoader that keeps dates/timestamps as strings instead of converting to datetime objects."""

    pass


# Remove the timestamp implicit resolver so dates like 2022-01-15 stay as strings
_SafeLoaderNoTimestamp.yaml_implicit_resolvers = {
    k: [(tag, regexp) for tag, regexp in v if tag != "tag:yaml.org,2002:timestamp"]
    for k, v in _SafeLoaderNoTimestamp.yaml_implicit_resolvers.copy().items()
}


def resolve_data_contract_dict(
    data_contract_location: str = None,
    data_contract_str: str = None,
    data_contract: OpenDataContractStandard = None,
) -> dict:
    """Resolve a data contract and return it as a dictionary."""
    if data_contract_location is not None:
        return _to_yaml(read_resource(data_contract_location))
    elif data_contract_str is not None:
        return _to_yaml(data_contract_str)
    elif data_contract is not None:
        return data_contract.model_dump()
    else:
        raise DataContractException(
            type="lint",
            result=ResultEnum.failed,
            name="Check that data contract YAML is valid",
            reason="Data contract needs to be provided",
            engine="datacontract",
        )


def resolve_data_contract(
    data_contract_location: str = None,
    data_contract_str: str = None,
    data_contract: OpenDataContractStandard = None,
    schema_location: str = None,
    inline_definitions: bool = False,
) -> OpenDataContractStandard:
    """Resolve and parse a data contract from various sources."""
    if data_contract_location is not None:
        return resolve_data_contract_from_location(
            data_contract_location, schema_location, inline_definitions
        )
    elif data_contract_str is not None:
        return _resolve_data_contract_from_str(data_contract_str, schema_location, inline_definitions)
    elif data_contract is not None:
        return data_contract
    else:
        raise DataContractException(
            type="lint",
            result=ResultEnum.failed,
            name="Check that data contract YAML is valid",
            reason="Data contract needs to be provided",
            engine="datacontract",
        )


def resolve_data_contract_from_location(
    location, schema_location: str = None, inline_definitions: bool = False
) -> OpenDataContractStandard:
    data_contract_str = read_resource(location)
    return _resolve_data_contract_from_str(data_contract_str, schema_location, inline_definitions)


def inline_definitions_into_data_contract(data_contract: OpenDataContractStandard):
    """Inline any definition references into the schema properties."""
    if data_contract.schema_ is None:
        return

    for schema_obj in data_contract.schema_:
        if schema_obj.properties:
            for prop in schema_obj.properties:
                inline_definition_into_property(prop, data_contract)


def inline_definition_into_property(prop: SchemaProperty, data_contract: OpenDataContractStandard):
    """Recursively inline definitions into a property and its nested properties."""
    # Iterate over items for arrays
    if prop.items is not None:
        inline_definition_into_property(prop.items, data_contract)

    # Iterate over nested properties
    if prop.properties is not None:
        for nested_prop in prop.properties:
            inline_definition_into_property(nested_prop, data_contract)

    # No definition $ref support in ODCS at the moment
    # ODCS uses a different approach - definitions would be handled differently


def _resolve_data_contract_from_str(
    data_contract_str, schema_location: str = None, inline_definitions: bool = False
) -> OpenDataContractStandard:
    yaml_dict = _to_yaml(data_contract_str)

    if is_open_data_product_standard(yaml_dict):
        logging.info("Cannot import ODPS, as not supported")
        raise DataContractException(
            type="schema",
            result=ResultEnum.failed,
            name="Parse ODCS contract",
            reason="Cannot parse ODPS product",
            engine="datacontract",
        )

    if is_open_data_contract_standard(yaml_dict):
        logging.info("Importing ODCS v3")
        # Validate the ODCS schema
        if schema_location is None:
            schema_location = resources.files("datacontract").joinpath("schemas", "odcs-3.1.0.schema.json")
        _validate_json_schema(yaml_dict, schema_location)

        # Parse ODCS directly
        odcs = _parse_odcs_from_dict(yaml_dict)
        if inline_definitions:
            inline_definitions_into_data_contract(odcs)
        return odcs

    # For DCS format, we need to convert it to ODCS
    logging.info("Importing DCS format - converting to ODCS")
    from datacontract.imports.dcs_importer import convert_dcs_to_odcs, parse_dcs_from_dict

    dcs = parse_dcs_from_dict(yaml_dict)
    odcs = convert_dcs_to_odcs(dcs)
    if inline_definitions:
        inline_definitions_into_data_contract(odcs)
    return odcs


def _parse_odcs_from_dict(yaml_dict: dict) -> OpenDataContractStandard:
    """Parse ODCS from a dictionary."""
    try:
        return OpenDataContractStandard(**yaml_dict)
    except Exception as e:
        raise DataContractException(
            type="schema",
            name="Parse ODCS contract",
            reason=f"Failed to parse ODCS contract: {str(e)}",
            engine="datacontract",
            original_exception=e,
        )


def _to_yaml(data_contract_str) -> dict:
    try:
        return yaml.load(data_contract_str, Loader=_SafeLoaderNoTimestamp)
    except Exception as e:
        logging.warning(f"Cannot parse YAML. Error: {str(e)}")
        raise DataContractException(
            type="lint",
            result="failed",
            name="Check that data contract YAML is valid",
            reason=f"Cannot parse YAML. Error: {str(e)}",
            engine="datacontract",
        )


def _validate_json_schema(yaml_str, schema_location: str | Path = None):
    logging.debug(f"Linting data contract with schema at {schema_location}")
    schema = fetch_schema(schema_location)
    try:
        fastjsonschema.validate(schema, yaml_str, use_default=False)
        logging.debug("YAML data is valid.")
    except JsonSchemaValueException as e:
        logging.warning(f"Data Contract YAML is invalid. Validation error: {e.message}")
        raise DataContractException(
            type="lint",
            result=ResultEnum.failed,
            name="Check that data contract YAML is valid",
            reason=e.message,
            engine="datacontract",
        )
    except Exception as e:
        logging.warning(f"Data Contract YAML is invalid. Validation error: {str(e)}")
        raise DataContractException(
            type="lint",
            result=ResultEnum.failed,
            name="Check that data contract YAML is valid",
            reason=str(e),
            engine="datacontract",
        )
