import typer
from typing_extensions import Annotated

from datacontract.cli import app, debug_option, enable_debug_logging
from datacontract.integration.entropy_data import (
    publish_data_contract_to_entropy_data,
)
from datacontract.lint.resolve import resolve_data_contract_dict


@app.command(
    name="publish",
    epilog="Example: datacontract publish datacontract.yaml",
)
def publish(
    location: Annotated[
        str,
        typer.Argument(help="The location (url or path) of the data contract yaml."),
    ] = "datacontract.yaml",
    schema: Annotated[
        str,
        typer.Option("--json-schema", help="The location (url or path) of the ODCS JSON Schema"),
    ] = None,
    ssl_verification: Annotated[
        bool,
        typer.Option(help="SSL verification when publishing the data contract."),
    ] = True,
    debug: debug_option = None,
):
    """
    Publish the data contract to the Entropy Data.
    """
    enable_debug_logging(debug)

    publish_data_contract_to_entropy_data(
        data_contract_dict=resolve_data_contract_dict(location),
        ssl_verification=ssl_verification,
    )
