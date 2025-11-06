from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from datacontract.export.exporter import Exporter, _check_models_for_export
from datacontract.model.data_contract_specification import (
    DataContractSpecification,
    Model,
)


class CustomExporter(Exporter):
    """Exporter implementation for converting data contracts to a custom Jinja template."""

    def export(
        self,
        data_contract: DataContractSpecification,
        model: str | None,
        server: str,
        sql_server_type: str,
        export_args: dict,
    ) -> str:
        """Exports a data contract to custom format with Jinja."""
        template = export_args.get("template")
        if template is None:
            raise RuntimeError("Export to custom requires template argument.")

        if model and model != "all":
            model_name, model_obj = _check_models_for_export(data_contract, model, self.export_format)
            return to_custom(data_contract, template, model_name=model_name, model=model_obj)
        else:
            return to_custom(data_contract, template)


def to_custom(
    data_contract: DataContractSpecification,
    template_path: Path,
    model_name: str | None = None,
    model: Model | None = None,
) -> str:
    template = get_template(template_path)
    context = {"data_contract": data_contract}
    if model is not None:
        context["model"] = model
        context["model_name"] = model_name
    return template.render(**context)


def get_template(path: Path):
    absolute_path = Path(path).resolve()
    env = Environment(loader=FileSystemLoader(str(absolute_path.parent)))
    return env.get_template(path.name)
