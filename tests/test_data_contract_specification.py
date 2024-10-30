import unittest
from uuid import uuid4

from datacontract.model.data_contract_specification import DataContractSpecification


class DataContractSpecificationException(unittest.TestCase):
    def test_from_file_raises_exception_if_file_does_not_exist(self):
        with self.assertRaises(FileNotFoundError):
            DataContractSpecification.from_file(f"{uuid4().hex}.yaml")
