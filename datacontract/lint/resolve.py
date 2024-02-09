import logging

import fastjsonschema
import yaml
from fastjsonschema import JsonSchemaValueException

from datacontract.lint.files import read_file
from datacontract.lint.schema import fetch_schema
from datacontract.lint.urls import fetch_resource
from datacontract.model.data_contract_specification import \
    DataContractSpecification
from datacontract.model.exceptions import DataContractException


def resolve_data_contract(
    data_contract_location: str = None,
    data_contract_str: str = None,
    data_contract: DataContractSpecification = None,
) -> DataContractSpecification:
    if data_contract_location is not None:
        return resolve_data_contract_from_location(data_contract_location)
    elif data_contract_str is not None:
        return resolve_data_contract_from_str(data_contract_str)
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


def resolve_data_contract_from_location(location) -> DataContractSpecification:
    if location.startswith("http://") or location.startswith("https://"):
        data_contract_str = fetch_resource(location)
    else:
        data_contract_str = read_file(location)
    return resolve_data_contract_from_str(data_contract_str)


def resolve_data_contract_from_str(data_contract_str):
    data_contract_yaml_dict = to_yaml(data_contract_str)
    validate(data_contract_yaml_dict)
    return DataContractSpecification(**data_contract_yaml_dict)


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


def validate(data_contract_yaml):
    schema = fetch_schema()
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
