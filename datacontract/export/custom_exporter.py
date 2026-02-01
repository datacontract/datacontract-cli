from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from open_data_contract_standard.model import OpenDataContractStandard, SchemaObject

from datacontract.export.exporter import Exporter, _check_schema_name_for_export


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

        if schema_name and schema_name != "all":
            schema_name, model_obj = _check_schema_name_for_export(data_contract, schema_name, self.export_format)
            return to_custom(data_contract, template, schema_name=schema_name, schema=model_obj)
        else:
            return to_custom(data_contract, template)


def to_custom(
    data_contract: OpenDataContractStandard,
    template_path: Path,
    schema_name: str | None = None,
    schema: SchemaObject | None = None,
) -> str:
    template = get_template(template_path)
    context = {"data_contract": data_contract}
    if schema is not None:
        context["schema"] = schema
        context["schema_name"] = schema_name
    return template.render(**context)


def get_template(path: Path):
    absolute_path = Path(path).resolve()
    env = Environment(loader=FileSystemLoader(str(absolute_path.parent)))
    return env.get_template(path.name)
