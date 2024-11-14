import os
##### TDOD: add import for Py protobuf 3 library
from datacontract.imports.importer import Importer
from datacontract.model.data_contract_specification import DataContractSpecification, Model, Field, Example, Server


class ProtoBufImporter(Importer):
    def import_source(
        self, data_contract_specification: DataContractSpecification, source: str, import_args: dict
    ) -> DataContractSpecification:
        return import_protobuf(data_contract_specification, self.import_format, source)


def import_protobuf(data_contract_specification: DataContractSpecification, format: str, source: str):
    include_example = False

    ##### TDOD: add impl.
    return data_contract_specification


def map_type_from_pandas(sql_type: str):
    if sql_type is None:
        return None

    sql_type_normed = sql_type.lower().strip()

    ##### TDOD: add impl.
