import yaml
from jinja2 import Environment, PackageLoader, select_autoescape

from datacontract.model.data_contract_specification import \
    DataContractSpecification


def to_html(data_contract_spec: DataContractSpecification) -> str:
    # Load templates from templates folder
    file_loader = PackageLoader("datacontract", "templates")
    env = Environment(
        loader=file_loader,
        autoescape=select_autoescape(
            enabled_extensions=('html', 'xml'),
            default_for_string=True,
        )
    )

    # Load the required template
    template = env.get_template('datacontract.html')

    if data_contract_spec.quality is not None and isinstance(data_contract_spec.quality.specification, str):
        quality_specification = data_contract_spec.quality.specification
    elif data_contract_spec.quality is not None and isinstance(data_contract_spec.quality.specification, object):
        if data_contract_spec.quality.type == "great-expectations":
            quality_specification = yaml.dump(data_contract_spec.quality.specification, sort_keys=False, default_style = "|")
        else:
            quality_specification = yaml.dump(data_contract_spec.quality.specification, sort_keys=False)
    else:
        quality_specification = None

    # Render the template with necessary data
    html_string = template.render(
        datacontract=data_contract_spec,
        quality_specification=quality_specification
    )

    return html_string
