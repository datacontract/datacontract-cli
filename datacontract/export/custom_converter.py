from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from open_data_contract_standard.model import OpenDataContractStandard

from datacontract.export.exporter import Exporter, Spec
from datacontract.model.data_contract_specification import (
    DataContractSpecification,
    Model,
)


class CustomExporter(Exporter):
    """Exporter implementation for converting data contracts to Markdown."""

    def export(
        self,
        data_contract: DataContractSpecification | OpenDataContractStandard,
        model: Model,
        server: str,
        sql_server_type: str,
        export_args: dict,
        spec: Spec = Spec.datacontract_specification
    ) -> str:
        """Exports a data contract to custom format with Jinja."""
        template = export_args.get("template")
        if template is None:
            raise RuntimeError("Export to custom requires template argument.")

        return to_custom(data_contract, template, spec)


def to_custom(data_contract: DataContractSpecification | OpenDataContractStandard, template_path: str, spec: Spec = Spec.datacontract_specification) -> str:
    template = get_template(Path(template_path))

    # Add the specification value to the rendering context
    rendered_output = template.render(data_contract=data_contract, spec=spec.value)
    return rendered_output


def get_template(path: Path):
    abosolute_path = Path(path).resolve()
    env = Environment(loader=FileSystemLoader(str(abosolute_path.parent)))
    return env.get_template(path.name)
