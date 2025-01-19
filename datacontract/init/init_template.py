import importlib.resources as resources
import logging

import requests

DEFAULT_DATA_CONTRACT_INIT_TEMPLATE = "datacontract-1.1.0.init.yaml"


def get_init_template(location: str = None) -> str:
    if location is None:
        logging.info("Use default bundled template " + DEFAULT_DATA_CONTRACT_INIT_TEMPLATE)
        schemas = resources.files("datacontract")
        template = schemas.joinpath("schemas", DEFAULT_DATA_CONTRACT_INIT_TEMPLATE)
        with template.open("r") as file:
            return file.read()
    elif location.startswith("http://") or location.startswith("https://"):
        return requests.get(location).text
    else:
        with open(location, "r") as file:
            return file.read()
