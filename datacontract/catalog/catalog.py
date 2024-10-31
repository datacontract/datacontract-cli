from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pytz
from jinja2 import Environment, PackageLoader, select_autoescape

from datacontract.data_contract import DataContract
from datacontract.export.html_export import get_version
from datacontract.model.data_contract_specification import DataContractSpecification


def create_data_contract_html(contracts, file: Path, path: Path, schema: str):
    data_contract = DataContract(
        data_contract_file=f"{file.absolute()}", inline_definitions=True, inline_quality=True, schema_location=schema
    )
    html = data_contract.export(export_format="html")
    spec = data_contract.get_data_contract_specification()
    file_without_suffix = file.with_suffix(".html")
    html_filepath = path / file_without_suffix
    html_filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(html_filepath, "w") as f:
        f.write(html)
    contracts.append(
        DataContractView(
            html_filepath=html_filepath,
            html_link=file_without_suffix,
            spec=spec,
        )
    )
    print(f"Created {html_filepath}")


@dataclass
class DataContractView:
    """Class for keeping track of an item in inventory."""

    html_filepath: Path
    html_link: Path
    spec: DataContractSpecification


def create_index_html(contracts, path):
    index_filepath = path / "index.html"
    with open(index_filepath, "w") as f:
        # Load templates from templates folder
        package_loader = PackageLoader("datacontract", "templates")
        env = Environment(
            loader=package_loader,
            autoescape=select_autoescape(
                enabled_extensions="html",
                default_for_string=True,
            ),
        )

        # Load the required template
        # needs to be included in /MANIFEST.in
        template = env.get_template("index.html")

        # needs to be included in /MANIFEST.in
        style_content, _, _ = package_loader.get_source(env, "style/output.css")

        tz = pytz.timezone("UTC")
        now = datetime.now(tz)
        formatted_date = now.strftime("%d %b %Y %H:%M:%S UTC")
        datacontract_cli_version = get_version()

        # Render the template with necessary data
        html_string = template.render(
            style=style_content,
            formatted_date=formatted_date,
            datacontract_cli_version=datacontract_cli_version,
            contracts=contracts,
            contracts_size=len(contracts),
            owners=sorted(set(dc.spec.info.owner for dc in contracts if dc.spec.info.owner)),
        )
        f.write(html_string)
    print(f"Created {index_filepath}")
