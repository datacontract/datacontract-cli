import os

import typer
from typing_extensions import Annotated

from datacontract.cli import app, console, debug_option, enable_debug_logging
from datacontract.init.init_template import get_init_template


@app.command(
    name="init",
    epilog="Example: datacontract init datacontract.yaml",
)
def init(
    location: Annotated[
        str, typer.Argument(help="The location of the data contract file to create.")
    ] = "datacontract.yaml",
    template: Annotated[str, typer.Option(help="URL of a template or data contract")] = None,
    overwrite: Annotated[bool, typer.Option(help="Replace the existing datacontract.yaml")] = False,
    debug: debug_option = None,
):
    """
    Create an empty data contract.
    """
    enable_debug_logging(debug)

    if not overwrite and os.path.exists(location):
        console.print("File already exists, use --overwrite to overwrite")
        raise typer.Exit(code=1)
    template_str = get_init_template(template)
    with open(location, "w") as f:
        f.write(template_str)
    console.print("📄 data contract written to " + location)
