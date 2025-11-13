import os
from urllib.parse import urlparse

import fsspec

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
    elif location.startswith("sftp://"):
        fs = setup_sftp_filesystem(location)
        with fs.open(location, "r") as file:
            return file.read()
    else:
        return read_file(location)

def setup_sftp_filesystem(url:str):
    parsed_url = urlparse(url)
    hostname = parsed_url.hostname if parsed_url.hostname is not None else "127.0.0.1"
    port = parsed_url.port if parsed_url.port is not None else 22
    sftp_user = os.getenv("DATACONTRACT_SFTP_USER")
    sftp_password = os.getenv("DATACONTRACT_SFTP_PASSWORD")
    if sftp_user is None or sftp_password is None:
        raise ValueError("Error: Environment variable DATACONTRACT_SFTP_USER is not set")
    if sftp_password is None :
        raise ValueError("Error: Environment variable DATACONTRACT_SFTP_PASSWORD is not set")
    return  fsspec.filesystem("sftp", host=hostname,port=port,username=sftp_user,password=sftp_password)

