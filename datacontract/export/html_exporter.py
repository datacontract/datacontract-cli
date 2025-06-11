import datetime
import logging
from importlib.metadata import version

import jinja_partials
import pytz
import yaml
from jinja2 import Environment, PackageLoader, select_autoescape
from open_data_contract_standard.model import OpenDataContractStandard

from datacontract.export.exporter import Exporter
from datacontract.export.mermaid_exporter import to_mermaid
from datacontract.model.data_contract_specification import DataContractSpecification


class HtmlExporter(Exporter):
    def export(self, data_contract, model, server, sql_server_type, export_args) -> dict:
        return to_html(data_contract)


def to_html(data_contract_spec: DataContractSpecification | OpenDataContractStandard) -> str:
    # Load templates from templates folder
    package_loader = PackageLoader("datacontract", "templates")
    env = Environment(
        loader=package_loader,
        autoescape=select_autoescape(
            enabled_extensions="html",
            default_for_string=True,
        ),
    )
    # Set up for partials
    jinja_partials.register_environment(env)

    # Load the required template
    # needs to be included in /MANIFEST.in
    template_file = "datacontract.html"
    if isinstance(data_contract_spec, OpenDataContractStandard):
        template_file = "datacontract_odcs.html"

    template = env.get_template(template_file)

    style_content, _, _ = package_loader.get_source(env, "style/output.css")

    quality_specification = None
    if isinstance(data_contract_spec, DataContractSpecification):
        if data_contract_spec.quality is not None and isinstance(data_contract_spec.quality.specification, str):
            quality_specification = data_contract_spec.quality.specification
        elif data_contract_spec.quality is not None and isinstance(data_contract_spec.quality.specification, object):
            if data_contract_spec.quality.type == "great-expectations":
                quality_specification = yaml.dump(
                    data_contract_spec.quality.specification, sort_keys=False, default_style="|"
                )
            else:
                quality_specification = yaml.dump(data_contract_spec.quality.specification, sort_keys=False)

    datacontract_yaml = data_contract_spec.to_yaml()

    # Get the mermaid diagram
    mermaid_diagram = to_mermaid(data_contract_spec)

    # Render the template with necessary data
    html_string = template.render(
        datacontract=data_contract_spec,
        quality_specification=quality_specification,
        style=style_content,
        datacontract_yaml=datacontract_yaml,
        formatted_date=_formatted_date(),
        datacontract_cli_version=get_version(),
        mermaid_diagram=mermaid_diagram,
    )

    return html_string


def _formatted_date() -> str:
    tz = pytz.timezone("UTC")
    now = datetime.datetime.now(tz)
    return now.strftime("%d %b %Y %H:%M:%S UTC")


def get_version() -> str:
    try:
        return version("datacontract_cli")
    except Exception as e:
        logging.debug("Ignoring exception", e)
        return ""
