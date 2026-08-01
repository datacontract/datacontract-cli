from datacontract.config import Config
from datacontract.lint.files import read_file
from datacontract.lint.urls import fetch_resource


def read_resource(location: str, config: Config | None = None) -> str:
    """
    Read a resource from a given location.

    If the location is a URL, fetch the resource from the web. API-Keys are supported.
    Otherwise, read the resource from a local file.

    Args:
        location (str): The location of the resource, either a URL or a file path.
        config: Optional credentials for authenticated URLs.

    Returns:
        str: The content of the resource.
    """
    if location.startswith("http://") or location.startswith("https://"):
        return fetch_resource(location, config)
    else:
        return read_file(location)
