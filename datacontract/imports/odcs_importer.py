import yaml

from datacontract.imports.importer import Importer
from datacontract.lint.resources import read_resource
from datacontract.model.data_contract_specification import (
    DataContractSpecification,
)
from datacontract.model.exceptions import DataContractException


class OdcsImporter(Importer):
    def import_source(
        self, data_contract_specification: DataContractSpecification, source: str, import_args: dict
    ) -> DataContractSpecification:
        return import_odcs(data_contract_specification, source)


def import_odcs(data_contract_specification: DataContractSpecification, source: str) -> DataContractSpecification:
    try:
        odcs_contract = yaml.safe_load(read_resource(source))

    except Exception as e:
        raise DataContractException(
            type="schema",
            name="Parse ODCS contract",
            reason=f"Failed to parse odcs contract from {source}",
            engine="datacontract",
            original_exception=e,
        )

    odcs_kind = odcs_contract.get("kind")
    odcs_api_version = odcs_contract.get("apiVersion")

    # if odcs_kind is not DataContract throw exception
    if odcs_kind != "DataContract":
        raise DataContractException(
            type="schema",
            name="Importing ODCS contract",
            reason=f"Unsupported ODCS kind: {odcs_kind}. Is this a valid ODCS data contract?",
            engine="datacontract",
        )

    if odcs_api_version.startswith("v2."):
        from datacontract.imports.odcs_v2_importer import import_odcs_v2

        return import_odcs_v2(data_contract_specification, source)
    elif odcs_api_version.startswith("v3."):
        from datacontract.imports.odcs_v3_importer import import_odcs_v3

        return import_odcs_v3(data_contract_specification, source)
    else:
        raise DataContractException(
            type="schema",
            name="Importing ODCS contract",
            reason=f"Unsupported ODCS API version: {odcs_api_version}",
            engine="datacontract",
        )
