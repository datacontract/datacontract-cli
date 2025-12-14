import yaml
from open_data_contract_standard.model import OpenDataContractStandard

from datacontract.imports.importer import Importer
from datacontract.lint.resources import read_resource
from datacontract.model.exceptions import DataContractException


class OdcsImporter(Importer):
    def import_source(
        self, source: str, import_args: dict
    ) -> OpenDataContractStandard:
        return import_odcs(source)


def import_odcs(source: str) -> OpenDataContractStandard:
    """Import an ODCS file directly - since ODCS is now the internal format, this is simpler."""
    try:
        odcs_yaml = yaml.safe_load(read_resource(source))
    except Exception as e:
        raise DataContractException(
            type="schema",
            name="Parse ODCS contract",
            reason=f"Failed to parse odcs contract from {source}",
            engine="datacontract",
            original_exception=e,
        )

    odcs_kind = odcs_yaml.get("kind")
    odcs_api_version = odcs_yaml.get("apiVersion")

    if odcs_kind != "DataContract":
        raise DataContractException(
            type="schema",
            name="Importing ODCS contract",
            reason=f"Unsupported ODCS kind: {odcs_kind}. Is this a valid ODCS data contract?",
            engine="datacontract",
        )

    if odcs_api_version.startswith("v2."):
        raise DataContractException(
            type="schema",
            name="Importing ODCS contract",
            reason=f"Unsupported ODCS API version: {odcs_api_version}. Only v3.x is supported.",
            engine="datacontract",
        )
    elif odcs_api_version.startswith("v3."):
        # Parse directly as ODCS
        return OpenDataContractStandard.model_validate(odcs_yaml)
    else:
        raise DataContractException(
            type="schema",
            name="Importing ODCS contract",
            reason=f"Unsupported ODCS API version: {odcs_api_version}",
            engine="datacontract",
        )
