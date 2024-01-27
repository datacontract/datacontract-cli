from enum import Enum

import typer
from typing_extensions import Annotated

from datacontract.data_contract import DataContract
from datacontract.init.download_datacontract_file import \
    download_datacontract_file, FileExistsException

app = typer.Typer(no_args_is_help=True)


@app.command()
def init(
    location: Annotated[str, typer.Argument(help="The location (url or path) of the data contract yaml to create.")] = "datacontract.yaml",
    template: Annotated[str, typer.Option(help="URL of a template or data contract")] = "https://datacontract.com/datacontract.init.yaml",
    overwrite: Annotated[bool, typer.Option(help="Replace the existing datacontract.yaml")] = False,
):
    try:
        download_datacontract_file(location, template, overwrite)
    except FileExistsException:
        print("File already exists, use --overwrite-file to overwrite")
        raise typer.Exit(code=1)
    else:
        print("📄 data contract written to " + location)


@app.command()
def lint(
    location: Annotated[str, typer.Argument(help="The location (url or path) of the data contract yaml.")] = "datacontract.yaml",
):
    run = DataContract(data_contract_file=location).lint()
    _handle_result(run)


@app.command()
def test(
    location: Annotated[str, typer.Argument(help="The location (url or path) of the data contract yaml.")] = "datacontract.yaml",
    server: Annotated[str, typer.Option(
        help="The server configuration to run the schema and quality tests. "
             "Use the key of the server object in the data contract yaml file "
             "to refer to a server, e.g., `production`, or `all` for all "
             "servers (default).")] = "all",
    publish: Annotated[str, typer.Option(
        help="")] = None,
):
    """
    Run schema and quality tests on configured servers.
    """
    print(f"Testing {location}")
    run = DataContract(data_contract_file=location, publish_url=publish).test()
    _handle_result(run)


class ExportFormat(str, Enum):
    jsonschema = "jsonschema"
    sodacl = "sodacl"


@app.command()
def export(
    format: Annotated[ExportFormat, typer.Option(help="The export format.")],
    location: Annotated[str, typer.Argument(help="The location (url or path) of the data contract yaml.")] = "datacontract.yaml",
):
    """
    Convert data contract to a specific format. Exports to stdout.
    """
    # TODO exception handling
    result = DataContract(data_contract_file=location).export(format)
    print(result)


def _handle_result(run):
    if run.result == "passed":
        print(f"🟢 data contract is valid. Tested {len(run.checks)} checks.")
    else:
        print("🔴 data contract is invalid, found the following errors:")
        i = 1
        for check in run.checks:
            if check.result != "passed":
                print(str(++i) + ") " + check.reason)
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
