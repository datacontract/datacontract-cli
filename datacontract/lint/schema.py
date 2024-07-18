import json
import os
from typing import Dict, Any

import requests

from datacontract.model.exceptions import DataContractException


def fetch_schema(location: str = None) -> Dict[str, Any]:
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
        location = "https://datacontract.com/datacontract.schema.json"

    if location.startswith("http://") or location.startswith("https://"):
        response = requests.get(location)
        schema = response.json()
    else:
        if not os.path.exists(location):
            raise DataContractException(
                type="lint",
                name=f"Reading schema from {location}",
                reason=f"The file '{location}' does not exist.",
                engine="datacontract",
                result="error",
            )
        with open(location, "r") as file:
            schema = json.load(file)

    return schema
