from open_data_contract_standard.model import OpenDataContractStandard

from datacontract.imports.importer import Importer
from datacontract.imports.odcs_v3_importer import import_from_odcs_model
from datacontract.model.data_contract_specification import (
    DataContractSpecification,
)
from datacontract.model.exceptions import DataContractException


class ExcelImporter(Importer):
    def import_source(
        self, data_contract_specification: DataContractSpecification, source: str, import_args: dict
    ) -> DataContractSpecification:
        return import_excel(data_contract_specification, source)


def import_excel(data_contract_specification: DataContractSpecification, source: str) -> DataContractSpecification:
    try:
        odcs = import_excel_as_odcs(source)
        return import_from_odcs_model(data_contract_specification, odcs)
    except Exception as e:
        raise DataContractException(
            type="schema",
            name="Parse excel contract",
            reason=f"Failed to parse odcs contract from {source}",
            engine="datacontract",
            original_exception=e,
        )


def import_excel_as_odcs(excel_file_path: str) -> OpenDataContractStandard:
    return None
