from datacontract.export.exporter import Exporter
from datacontract.model.data_contract_specification import (
    DataContractSpecification,
    Model,
)


class CustomExporter(Exporter):
    """Exporter implementation for converting data contracts to Markdown."""

    def export(
        self,
        data_contract: DataContractSpecification,
        model: Model,
        server: str,
        sql_server_type: str,
        export_args: dict,
    ) -> str:
        """Exports a data contract to custom format with Jinja."""
        template = export_args.get("template")
        if template is None:
            raise RuntimeError("Export to custom requires template argument.")

        return to_custom(data_contract, template)


def to_custom(data_contract: DataContractSpecification, template: str) -> str:
    return ""
