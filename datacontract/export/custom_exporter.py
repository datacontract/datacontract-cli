from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from open_data_contract_standard.model import OpenDataContractStandard

from datacontract.export.exporter import Exporter


class CustomExporter(Exporter):
    """Exporter implementation for converting data contracts to custom format with Jinja."""

    def export(
        self,
        data_contract: OpenDataContractStandard,
        schema_name: str,
        server: str,
        sql_server_type: str,
        export_args: dict,
    ) -> str:
        """Exports a data contract to custom format with Jinja."""
        template = export_args.get("template")
        if template is None:
            raise RuntimeError("Export to custom requires template argument.")

        return to_custom(data_contract, template)


def to_custom(data_contract: OpenDataContractStandard, template_path: Path) -> str:
    template = get_template(template_path)
    rendered_sql = template.render(data_contract=data_contract)
    return rendered_sql


def get_template(path: Path):
    abosolute_path = Path(path).resolve()
    env = Environment(loader=FileSystemLoader(str(abosolute_path.parent)))
    return env.get_template(path.name)
