import os

import requests


def download_datacontract_file(file_path: str, from_url: str, overwrite_file: bool):
    if not overwrite_file and os.path.exists(file_path):
        raise FileExistsException()

    with requests.get(from_url) as response:
        response.raise_for_status()
        with open(file_path, "w") as f:
            f.write(response.text)


class FileExistsException(Exception):
    pass
