import json
import os

import requests

from datacontract.model.exceptions import DataContractException


def fetch_schema(location: str = None):
    if location is None:
        location = "https://raw.githubusercontent.com/datacontract/datacontract-specification/f919bb6bb14bbcb29e089fd987754ab14fa91bfd/datacontract.schema.json"  # TODO change back

    if location.startswith("http://") or location.startswith("https://"):
        response = requests.get(location)
        return response.json()
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
            file_content = file.read()
        return json.loads(file_content)
