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
    It also updates the FieldType enum in the schema to include "enum" and "map" if they're not already present.

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

    # Update the FieldType enum to include "enum" and "map" if it's not already there
    # this piece of code can be removed if ADMINS modify the datacontract.schema.json
    if "$defs" in schema and "FieldType" in schema["$defs"]:
        field_type_enum = schema["$defs"]["FieldType"].get("enum", [])
        if "enum" not in field_type_enum or "map" not in field_type_enum:
            field_type_enum.extend(["enum", "map"])
            schema["$defs"]["FieldType"]["enum"] = field_type_enum

    return schema
