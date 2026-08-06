import typer
from typing_extensions import Annotated

from datacontract.cli import app, console, debug_option, enable_debug_logging
from datacontract.config import cli_config
from datacontract.data_contract import DataContract


@app.command(
    name="publish",
    epilog="Example: datacontract publish datacontract.yaml",
)
def publish(
    location: Annotated[
        str,
        typer.Argument(help="The location (url, s3 url, or local path) of the data contract yaml."),
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
    Publish the data contract to Entropy Data.
    """
    enable_debug_logging(debug)

    location_html = DataContract(
        data_contract_file=location,
        schema_location=schema,
        ssl_verification=ssl_verification,
        config=cli_config(),
    ).publish()

    console.print("✅ Published data contract successfully")
    if location_html is not None:
        console.print(f"🚀 Open {location_html}")
