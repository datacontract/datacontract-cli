import os

from datacontract.model.exceptions import DataContractException
from datacontract.model.run import ResultEnum


def read_file(path):
    if not os.path.exists(path):
        raise DataContractException(
            type="lint",
            name=f"Reading data contract from {path}",
            reason=f"The file '{path}' does not exist.",
            engine="datacontract-cli",
            result=ResultEnum.error,
        )
    with open(path, "r") as file:
        file_content = file.read()
    return file_content
