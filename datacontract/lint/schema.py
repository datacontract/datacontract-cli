import importlib.resources as resources
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict

import requests

from datacontract.model.exceptions import DataContractException
from datacontract.model.run import ResultEnum

DEFAULT_DATA_CONTRACT_SCHEMA = "datacontract-1.2.1.schema.json"


def fetch_schema(location: str | Path = None) -> Dict[str, Any]:
    """
    Fetch and return a JSON schema from a given location.

    This function retrieves a JSON schema either from a URL or a local file path.
    If no location is provided, it defaults to the DataContract schema URL.

    Args:
        location: The URL or file path of the schema.

    Returns:
        The JSON schema as a dictionary.

    Raises:
        DataContractException: If the specified local file does not exist.
        requests.RequestException: If there's an error fetching the schema from a URL.
        json.JSONDecodeError: If there's an error decoding the JSON schema.

    """
    if location is None:
        logging.info("Use default bundled schema " + DEFAULT_DATA_CONTRACT_SCHEMA)
        schemas = resources.files("datacontract")
        schema_file = schemas.joinpath("schemas", DEFAULT_DATA_CONTRACT_SCHEMA)
        with schema_file.open("r") as file:
            schema = json.load(file)
    else:
        # Convert Path objects to strings for string operations
        location_str = str(location)

        if location_str.startswith("http://") or location_str.startswith("https://"):
            logging.debug(f"Downloading schema from {location_str}")
            response = requests.get(location_str)
            schema = response.json()
        else:
            if not os.path.exists(location):
                raise DataContractException(
                    type="lint",
                    name=f"Reading schema from {location}",
                    reason=f"The file '{location}' does not exist.",
                    engine="datacontract",
                    result=ResultEnum.error,
                )

            logging.debug(f"Loading JSON schema locally at {location}")
            with open(location, "r") as file:
                schema = json.load(file)

    return schema
