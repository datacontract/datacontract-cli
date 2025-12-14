from uuid import uuid4

import pytest
from datacontract_specification.model import DataContractSpecification


def test_from_file_raises_exception_if_file_does_not_exist():
    with pytest.raises(FileNotFoundError):
        DataContractSpecification.from_file(f"{uuid4().hex}.yaml")
