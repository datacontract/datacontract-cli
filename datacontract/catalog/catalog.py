import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import pytz
from jinja2 import Environment, PackageLoader, select_autoescape
from open_data_contract_standard.model import OpenDataContractStandard

from datacontract.data_contract import DataContract
from datacontract.export.html_exporter import get_version


def _get_owner(odcs: OpenDataContractStandard) -> Optional[str]:
    """Get the owner from ODCS customProperties or team."""
    if odcs.team and odcs.team.name:
        return odcs.team.name
    if odcs.customProperties:
        for prop in odcs.customProperties:
            if prop.property == "owner":
                return prop.value
    return None


def create_data_contract_html(contracts, file: Path, path: Path, schema: str):
    logging.debug(f"Creating data contract html for file {file} and schema {schema}")
    data_contract = DataContract(
        data_contract_file=f"{file.absolute()}", inline_definitions=True, schema_location=schema
    )
    html = data_contract.export(export_format="html")
    odcs = data_contract.get_data_contract()
    file_without_suffix = file.with_suffix(".html")
    html_filepath = path / file_without_suffix
    html_filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(html_filepath, "w", encoding="utf-8") as f:
        f.write(html)
    contracts.append(
        DataContractView(
            html_filepath=html_filepath,
            html_link=file_without_suffix,
            odcs=odcs,
        )
    )
    print(f"Created {html_filepath}")


@dataclass
class _InfoView:
    """Unified info view for templates."""
    title: str
    version: str
    owner: Optional[str]
    description: Optional[str]


@dataclass
class _SpecView:
    """Unified spec view for templates, compatible with DCS template structure."""
    info: _InfoView
    models: dict


@dataclass
class DataContractView:
    """Class for keeping track of an item in inventory."""

    html_filepath: Path
    html_link: Path
    odcs: OpenDataContractStandard

    @property
    def spec(self) -> _SpecView:
        """Provide a DCS-compatible view for templates."""
        # Build models dict from ODCS schema
        models = {}
        if self.odcs.schema_:
            for schema in self.odcs.schema_:
                fields = {}
                if schema.properties:
                    for prop in schema.properties:
                        fields[prop.name] = {
                            "description": prop.description,
                        }
                models[schema.name] = {
                    "description": schema.description,
                    "fields": fields,
                }

        # Get description
        description = None
        if self.odcs.description:
            if isinstance(self.odcs.description, str):
                description = self.odcs.description
            elif hasattr(self.odcs.description, "purpose"):
                description = self.odcs.description.purpose

        return _SpecView(
            info=_InfoView(
                title=self.odcs.name or self.odcs.id or "",
                version=self.odcs.version or "",
                owner=_get_owner(self.odcs),
                description=description,
            ),
            models=models,
        )


def create_index_html(contracts, path):
    index_filepath = path / "index.html"
    with open(index_filepath, "w", encoding="utf-8") as f:
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
            owners=sorted(set(_get_owner(dc.odcs) for dc in contracts if _get_owner(dc.odcs))),
        )
        f.write(html_string)
    print(f"Created {index_filepath}")
