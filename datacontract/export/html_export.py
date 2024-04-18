import yaml
from jinja2 import Environment, PackageLoader, select_autoescape

from datacontract.model.data_contract_specification import \
    DataContractSpecification


def to_html(data_contract_spec: DataContractSpecification) -> str:
    # Load templates from templates folder
    package_loader = PackageLoader("datacontract", "templates")
    env = Environment(
        loader=package_loader,
        autoescape=select_autoescape(
            enabled_extensions=("html", "xml"),
            default_for_string=True,
        ),
    )

    # Load the required template
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

    # Render the template with necessary data
    html_string = template.render(
        datacontract=data_contract_spec,
        quality_specification=quality_specification,
        style=style_content,
        datacontract_yaml=datacontract_yaml,
    )

    return html_string
