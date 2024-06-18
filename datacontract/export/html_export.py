import datetime
import logging
from importlib.metadata import version

import jinja_partials
import pytz
import yaml
from jinja2 import Environment, PackageLoader, select_autoescape

from datacontract.model.data_contract_specification import DataContractSpecification
from datacontract.export.exporter import Exporter


class HtmlExporter(Exporter):
    def export(self, data_contract, model, server, sql_server_type, export_args) -> dict:
        return to_html(data_contract)


def to_html(data_contract_spec: DataContractSpecification) -> str:
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
    template = env.get_template("datacontract.html")

    if data_contract_spec.quality is not None and isinstance(data_contract_spec.quality.specification, str):
        quality_specification = data_contract_spec.quality.specification
    elif data_contract_spec.quality is not None and isinstance(data_contract_spec.quality.specification, object):
        if data_contract_spec.quality.type == "great-expectations":
            quality_specification = yaml.dump(
                data_contract_spec.quality.specification, sort_keys=False, default_style="|"
            )
        else:
            quality_specification = yaml.dump(data_contract_spec.quality.specification, sort_keys=False)
    else:
        quality_specification = None

    style_content, _, _ = package_loader.get_source(env, "style/output.css")

    datacontract_yaml = data_contract_spec.to_yaml()

    tz = pytz.timezone("UTC")
    now = datetime.datetime.now(tz)
    formatted_date = now.strftime("%d %b %Y %H:%M:%S UTC")
    datacontract_cli_version = get_version()

    # Render the template with necessary data
    html_string = template.render(
        datacontract=data_contract_spec,
        quality_specification=quality_specification,
        style=style_content,
        datacontract_yaml=datacontract_yaml,
        formatted_date=formatted_date,
        datacontract_cli_version=datacontract_cli_version,
    )

    return html_string


def get_version() -> str:
    try:
        return version("datacontract_cli")
    except Exception as e:
        logging.debug("Ignoring exception", e)
        return ""
