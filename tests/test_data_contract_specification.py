from uuid import uuid4

import pytest

from datacontract.model.data_contract_specification import DataContractSpecification


def test_from_file_raises_exception_if_file_does_not_exist():
    with pytest.raises(FileNotFoundError):
        DataContractSpecification.from_file(f"{uuid4().hex}.yaml")
