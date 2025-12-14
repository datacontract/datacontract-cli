"""ODCS V3 Exporter - Exports the internal ODCS model to YAML format."""

from open_data_contract_standard.model import OpenDataContractStandard

from datacontract.export.exporter import Exporter


class OdcsV3Exporter(Exporter):
    def export(self, data_contract, schema_name, server, sql_server_type, export_args) -> dict:
        return to_odcs_v3_yaml(data_contract)


def to_odcs_v3_yaml(data_contract: OpenDataContractStandard) -> str:
    """Export the internal ODCS model to YAML format.

    Since the internal model is now ODCS, this is a simple serialization.
    """
    return data_contract.to_yaml()


def to_odcs_v3(data_contract: OpenDataContractStandard) -> OpenDataContractStandard:
    """Return the internal ODCS model.

    Since the internal model is now ODCS, this is an identity function.
    """
    return data_contract
