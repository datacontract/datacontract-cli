from enum import Enum
from importlib import metadata
from typing import Iterable

import typer
from click import Context
from rich import box
from rich import print
from rich.table import Table
from typer.core import TyperGroup
from typing_extensions import Annotated

from datacontract.data_contract import DataContract
from datacontract.init.download_datacontract_file import \
    download_datacontract_file, FileExistsException


class OrderedCommands(TyperGroup):
    def list_commands(self, ctx: Context) -> Iterable[str]:
        return self.commands.keys()


app = typer.Typer(
    cls=OrderedCommands,
    no_args_is_help=True,
    add_completion=False,
)


def version_callback(value: bool):
    if value:
        print(metadata.version("datacontract-cli"))
        raise typer.Exit()


@app.callback()
def common(
    ctx: typer.Context,
    version: bool = typer.Option(None, "--version", help="Prints the current version.", callback=version_callback,
                                 is_eager=True),
):
    """
    The datacontract CLI is an open source command-line tool for working with Data Contracts (https://datacontract.com).

    It uses data contract YAML files to lint the data contract,
    connect to data sources and execute schema and quality tests,
    detect breaking changes, and export to different formats.
    """
    pass


@app.command()
def init(
    location: Annotated[str, typer.Argument(
        help="The location (url or path) of the data contract yaml to create.")] = "datacontract.yaml",
    template: Annotated[str, typer.Option(
        help="URL of a template or data contract")] = "https://datacontract.com/datacontract.init.yaml",
    overwrite: Annotated[bool, typer.Option(help="Replace the existing datacontract.yaml")] = False,
):
    """
    Download a datacontract.yaml template and write it to file.
    """
    try:
        download_datacontract_file(location, template, overwrite)
    except FileExistsException:
        print("File already exists, use --overwrite to overwrite")
        raise typer.Exit(code=1)
    else:
        print("📄 data contract written to " + location)


@app.command()
def lint(
    location: Annotated[
        str, typer.Argument(help="The location (url or path) of the data contract yaml.")] = "datacontract.yaml",
    schema: Annotated[
        str, typer.Option(help="The location (url or path) of the Data Contract Specification JSON Schema")] = "https://datacontract.com/datacontract.schema.json",
):
    """
    Validate that the datacontract.yaml is correctly formatted.
    """
    run = DataContract(data_contract_file=location, schema_location=schema).lint()
    _handle_result(run)


@app.command()
def test(
    location: Annotated[
        str, typer.Argument(help="The location (url or path) of the data contract yaml.")] = "datacontract.yaml",
    schema: Annotated[
        str, typer.Option(help="The location (url or path) of the Data Contract Specification JSON Schema")] = "https://datacontract.com/datacontract.schema.json",
    server: Annotated[str, typer.Option(
        help="The server configuration to run the schema and quality tests. "
             "Use the key of the server object in the data contract yaml file "
             "to refer to a server, e.g., `production`, or `all` for all "
             "servers (default).")] = "all",
    examples: Annotated[bool, typer.Option(
        help="Run the schema and quality tests on the example data within the data contract.")] = None,
    publish: Annotated[str, typer.Option(
        help="The url to publish the results after the test")] = None,
    logs: Annotated[bool, typer.Option(
        help="Print logs")] = False,
):
    """
    Run schema and quality tests on configured servers.
    """
    print(f"Testing {location}")
    if server == "all":
        server = None
    run = DataContract(data_contract_file=location, schema_location=schema, publish_url=publish, server=server, examples=examples).test()
    if logs:
        _print_logs(run)
    _handle_result(run)


class ExportFormat(str, Enum):
    jsonschema = "jsonschema"
    sodacl = "sodacl"
    dbt = "dbt"
    odcs = "odcs"


@app.command()
def export(
    format: Annotated[ExportFormat, typer.Option(help="The export format.")],
    location: Annotated[
        str, typer.Argument(help="The location (url or path) of the data contract yaml.")] = "datacontract.yaml",
):
    """
    Convert data contract to a specific format. Prints to stdout.
    """
    # TODO exception handling
    result = DataContract(data_contract_file=location).export(format)
    print(result)


def _handle_result(run):
    _print_table(run)
    if run.result == "passed":
        print(f"🟢 data contract is valid. Run {len(run.checks)} checks. Took {(run.timestampEnd - run.timestampStart).total_seconds()} seconds.")
    else:
        print("🔴 data contract is invalid, found the following errors:")
        i = 1
        for check in run.checks:
            if check.result != "passed":
                print(str(++i) + ") " + check.reason)
        raise typer.Exit(code=1)


def _print_table(run):
    table = Table(box=box.ROUNDED)
    table.add_column("Result", no_wrap=True)
    table.add_column("Check", max_width=100)
    table.add_column("Field", max_width=32)
    table.add_column("Details", max_width=50)
    for check in run.checks:
        table.add_row(with_markup(check.result), check.name, to_field(run, check), check.details)
    print(table)


def to_field(run, check):
    models = [c.model for c in run.checks]
    if len(set(models)) > 1:
        if check.field is None:
            return check.model
        return check.model + "." + check.field
    else:
        return check.field




def _print_logs(run):
    print("\nLogs:")
    for log in run.logs:
        print(log.timestamp.strftime("%y-%m-%d %H:%M:%S"), log.level.ljust(5), log.message)


def with_markup(result):
    if result == "passed":
        return "[green]passed[/green]"
    if result == "warning":
        return "[yellow]warning[/yellow]"
    if result == "failed":
        return "[red]failed[/red]"
    if result == "error":
        return "[red]error[/red]"
    return result


if __name__ == "__main__":
    app()
