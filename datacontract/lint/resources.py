from datacontract.lint.files import read_file
from datacontract.lint.urls import fetch_resource


def read_resource(location: str) -> str:
    """
    Read a resource from a given location.

    If the location is a URL, fetch the resource from the web. API-Keys are supported.
    Otherwise, read the resource from a local file.

    Args:
        location (str): The location of the resource, either a URL or a file path.

    Returns:
        str: The content of the resource.
    """
    if location.startswith("http://") or location.startswith("https://"):
        return fetch_resource(location)
    else:
        return read_file(location)
