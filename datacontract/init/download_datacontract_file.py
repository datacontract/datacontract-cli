import os

import requests


def download_template_from_url(url: str) -> str:
    """
    Download the data contract template from the given URL.

    Args:
        url (str): The URL to download the data contract template from.

    Returns:
        str: The data contract template as a string.
    """
    with requests.get(url) as response:
        response.raise_for_status()
        return response.text


def download_datacontract_file(file_path: str, from_url: str, overwrite_file: bool):
    if not overwrite_file and os.path.exists(file_path):
        raise FileExistsException()

    with requests.get(from_url) as response:
        response.raise_for_status()
        return response.text
        with open(file_path, "w") as f:
            f.write(response.text)


class FileExistsException(Exception):
    pass
