from jinja2 import Environment, PackageLoader, select_autoescape

from datacontract.model.data_contract_specification import \
    DataContractSpecification


def to_html(data_contract_spec: DataContractSpecification) -> str:
    # Load templates from templates folder
    file_loader = PackageLoader("datacontract", "templates")
    env = Environment(loader=file_loader, autoescape=select_autoescape(
        enabled_extensions=('html', 'xml'),
        default_for_string=True,
    ))

    # Load the required template
    template = env.get_template('datacontract.html')

    # Render the template with necessary data
    html_string = template.render(datacontract=data_contract_spec)

    return html_string
