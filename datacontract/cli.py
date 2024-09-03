from importlib import metadata
from pathlib import Path
from typing import Iterable, Optional
from typing import List

import typer
import uvicorn
from click import Context
from rich import box
from rich.console import Console
from rich.table import Table
from typer.core import TyperGroup
from typing_extensions import Annotated

from datacontract import web
from datacontract.catalog.catalog import create_index_html, create_data_contract_html
from datacontract.data_contract import DataContract, ExportFormat
from datacontract.imports.importer import ImportFormat
from datacontract.init.download_datacontract_file import download_datacontract_file, FileExistsException
from datacontract.integration.datamesh_manager import publish_data_contract_to_datamesh_manager

DEFAULT_DATA_CONTRACT_SCHEMA_URL = "https://datacontract.com/datacontract.schema.json"

console = Console()


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
        console.print(metadata.version("datacontract-cli"))
        raise typer.Exit()


@app.callback()
def common(
    ctx: typer.Context,
    version: bool = typer.Option(
        None, "--version", help="Prints the current version.", callback=version_callback, is_eager=True
    ),
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
    location: Annotated[
        str, typer.Argument(help="The location (url or path) of the data contract yaml to create.")
    ] = "datacontract.yaml",
    template: Annotated[
        str, typer.Option(help="URL of a template or data contract")
    ] = "https://datacontract.com/datacontract.init.yaml",
    overwrite: Annotated[bool, typer.Option(help="Replace the existing datacontract.yaml")] = False,
):
    """
    Download a datacontract.yaml template and write it to file.
    """
    try:
        download_datacontract_file(location, template, overwrite)
    except FileExistsException:
        console.print("File already exists, use --overwrite to overwrite")
        raise typer.Exit(code=1)
    else:
        console.print("📄 data contract written to " + location)


@app.command()
def lint(
    location: Annotated[
        str, typer.Argument(help="The location (url or path) of the data contract yaml.")
    ] = "datacontract.yaml",
    schema: Annotated[
        str, typer.Option(help="The location (url or path) of the Data Contract Specification JSON Schema")
    ] = DEFAULT_DATA_CONTRACT_SCHEMA_URL,
):
    """
    Validate that the datacontract.yaml is correctly formatted.
    """
    run = DataContract(data_contract_file=location, schema_location=schema).lint()
    _handle_result(run)


@app.command()
def test(
    location: Annotated[
        str, typer.Argument(help="The location (url or path) of the data contract yaml.")
    ] = "datacontract.yaml",
    schema: Annotated[
        str, typer.Option(help="The location (url or path) of the Data Contract Specification JSON Schema")
    ] = DEFAULT_DATA_CONTRACT_SCHEMA_URL,
    server: Annotated[
        str,
        typer.Option(
            help="The server configuration to run the schema and quality tests. "
            "Use the key of the server object in the data contract yaml file "
            "to refer to a server, e.g., `production`, or `all` for all "
            "servers (default)."
        ),
    ] = "all",
    examples: Annotated[
        bool, typer.Option(help="Run the schema and quality tests on the example data within the data contract.")
    ] = None,
    publish: Annotated[str, typer.Option(help="The url to publish the results after the test")] = None,
    publish_to_opentelemetry: Annotated[
        bool,
        typer.Option(
            help="Publish the results to opentelemetry. Use environment variables to configure the OTLP endpoint, headers, etc."
        ),
    ] = False,
    logs: Annotated[bool, typer.Option(help="Print logs")] = False,
):
    """
    Run schema and quality tests on configured servers.
    """
    console.print(f"Testing {location}")
    if server == "all":
        server = None
    run = DataContract(
        data_contract_file=location,
        schema_location=schema,
        publish_url=publish,
        publish_to_opentelemetry=publish_to_opentelemetry,
        server=server,
        examples=examples,
    ).test()
    if logs:
        _print_logs(run)
    _handle_result(run)


@app.command()
def export(
    format: Annotated[ExportFormat, typer.Option(help="The export format.")],
    output: Annotated[
        Path,
        typer.Option(
            help="Specify the file path where the exported data will be saved. If no path is provided, the output will be printed to stdout."
        ),
    ] = None,
    server: Annotated[str, typer.Option(help="The server name to export.")] = None,
    model: Annotated[
        str,
        typer.Option(
            help="Use the key of the model in the data contract yaml file "
            "to refer to a model, e.g., `orders`, or `all` for all "
            "models (default)."
        ),
    ] = "all",
    # TODO: this should be a subcommand
    rdf_base: Annotated[
        Optional[str],
        typer.Option(help="[rdf] The base URI used to generate the RDF graph.", rich_help_panel="RDF Options"),
    ] = None,
    # TODO: this should be a subcommand
    sql_server_type: Annotated[
        Optional[str],
        typer.Option(
            help="[sql] The server type to determine the sql dialect. By default, it uses 'auto' to automatically detect the sql dialect via the specified servers in the data contract.",
            rich_help_panel="SQL Options",
        ),
    ] = "auto",
    location: Annotated[
        str, typer.Argument(help="The location (url or path) of the data contract yaml.")
    ] = "datacontract.yaml",
    schema: Annotated[
        str, typer.Option(help="The location (url or path) of the Data Contract Specification JSON Schema")
    ] = DEFAULT_DATA_CONTRACT_SCHEMA_URL,
):
    """
    Convert data contract to a specific format. console.prints to stdout.
    """
    # TODO exception handling
    result = DataContract(data_contract_file=location, schema_location=schema, server=server).export(
        export_format=format,
        model=model,
        server=server,
        rdf_base=rdf_base,
        sql_server_type=sql_server_type,
    )
    # Don't interpret console markup in output.
    if output is None:
        console.print(result, markup=False)
    else:
        with output.open("w") as f:
            f.write(result)
        console.print(f"Written result to {output}")


@app.command(name="import")
def import_(
    format: Annotated[ImportFormat, typer.Option(help="The format of the source file.")],
    source: Annotated[
        Optional[str], typer.Option(help="The path to the file or Glue Database that should be imported.")
    ] = None,
    glue_table: Annotated[
        Optional[List[str]],
        typer.Option(
            help="List of table ids to import from the Glue Database (repeat for multiple table ids, leave empty for all tables in the dataset)."
        ),
    ] = None,
    bigquery_project: Annotated[Optional[str], typer.Option(help="The bigquery project id.")] = None,
    bigquery_dataset: Annotated[Optional[str], typer.Option(help="The bigquery dataset id.")] = None,
    bigquery_table: Annotated[
        Optional[List[str]],
        typer.Option(
            help="List of table ids to import from the bigquery API (repeat for multiple table ids, leave empty for all tables in the dataset)."
        ),
    ] = None,
    unity_table_full_name: Annotated[
        Optional[str], typer.Option(help="Full name of a table in the unity catalog")
    ] = None,
    dbt_model: Annotated[
        Optional[List[str]],
        typer.Option(
            help="List of models names to import from the dbt manifest file (repeat for multiple models names, leave empty for all models in the dataset)."
        ),
    ] = None,
    dbml_schema: Annotated[
        Optional[List[str]],
        typer.Option(
            help="List of schema names to import from the DBML file (repeat for multiple schema names, leave empty for all tables in the file)."
        ),
    ] = None,
    dbml_table: Annotated[
        Optional[List[str]],
        typer.Option(
            help="List of table names to import from the DBML file (repeat for multiple table names, leave empty for all tables in the file)."
        ),
    ] = None,
):
    """
    Create a data contract from the given source location. Prints to stdout.
    """
    result = DataContract().import_from_source(
        format=format,
        source=source,
        glue_table=glue_table,
        bigquery_table=bigquery_table,
        bigquery_project=bigquery_project,
        bigquery_dataset=bigquery_dataset,
        unity_table_full_name=unity_table_full_name,
        dbt_model=dbt_model,
        dbml_schema=dbml_schema,
        dbml_table=dbml_table,
    )
    console.print(result.to_yaml())


@app.command(name="publish")
def publish(
    location: Annotated[
        str, typer.Argument(help="The location (url or path) of the data contract yaml.")
    ] = "datacontract.yaml",
    schema: Annotated[
        str, typer.Option(help="The location (url or path) of the Data Contract Specification JSON Schema")
    ] = DEFAULT_DATA_CONTRACT_SCHEMA_URL,
):
    """
    Publish the data contract to the Data Mesh Manager.
    """
    publish_data_contract_to_datamesh_manager(
        data_contract_specification=DataContract(
            data_contract_file=location, schema_location=schema
        ).get_data_contract_specification(),
    )


@app.command(name="catalog")
def catalog(
    files: Annotated[
        Optional[str], typer.Option(help="Glob pattern for the data contract files to include in the catalog.")
    ] = "*.yaml",
    output: Annotated[Optional[str], typer.Option(help="Output directory for the catalog html files.")] = "catalog/",
    schema: Annotated[
        str, typer.Option(help="The location (url or path) of the Data Contract Specification JSON Schema")
    ] = DEFAULT_DATA_CONTRACT_SCHEMA_URL,
):
    """
    Create an html catalog of data contracts.
    """
    path = Path(output)
    path.mkdir(parents=True, exist_ok=True)
    console.print(f"Created {output}")

    contracts = []
    for file in Path().glob(files):
        try:
            create_data_contract_html(contracts, file, path, schema)
        except Exception as e:
            console.print(f"Skipped {file} due to error: {e}")

    create_index_html(contracts, path)


@app.command()
def breaking(
    location_old: Annotated[str, typer.Argument(help="The location (url or path) of the old data contract yaml.")],
    location_new: Annotated[str, typer.Argument(help="The location (url or path) of the new data contract yaml.")],
):
    """
    Identifies breaking changes between data contracts. Prints to stdout.
    """

    # TODO exception handling
    result = DataContract(data_contract_file=location_old, inline_definitions=True).breaking(
        DataContract(data_contract_file=location_new, inline_definitions=True)
    )

    console.print(result.breaking_str())

    if not result.passed_checks():
        raise typer.Exit(code=1)


@app.command()
def changelog(
    location_old: Annotated[str, typer.Argument(help="The location (url or path) of the old data contract yaml.")],
    location_new: Annotated[str, typer.Argument(help="The location (url or path) of the new data contract yaml.")],
):
    """
    Generate a changelog between data contracts. Prints to stdout.
    """

    # TODO exception handling
    result = DataContract(data_contract_file=location_old, inline_definitions=True).changelog(
        DataContract(data_contract_file=location_new, inline_definitions=True)
    )

    console.print(result.changelog_str())


@app.command()
def diff(
    location_old: Annotated[str, typer.Argument(help="The location (url or path) of the old data contract yaml.")],
    location_new: Annotated[str, typer.Argument(help="The location (url or path) of the new data contract yaml.")],
):
    """
    PLACEHOLDER. Currently works as 'changelog' does.
    """

    # TODO change to diff output, not the changelog entries
    result = DataContract(data_contract_file=location_old, inline_definitions=True).changelog(
        DataContract(data_contract_file=location_new, inline_definitions=True)
    )

    console.print(result.changelog_str())


@app.command()
def serve(
    port: Annotated[int, typer.Option(help="Bind socket to this port.")] = 4242,
    host: Annotated[str, typer.Option(help="Bind socket to this host.")] = "127.0.0.1",
):
    """
    Start the datacontract web server.
    """

    uvicorn.run(web.app, port=port, host=host)


def _handle_result(run):
    _print_table(run)
    if run.result == "passed":
        console.print(
            f"🟢 data contract is valid. Run {len(run.checks)} checks. Took {(run.timestampEnd - run.timestampStart).total_seconds()} seconds."
        )
    else:
        console.print("🔴 data contract is invalid, found the following errors:")
        i = 1
        for check in run.checks:
            if check.result != "passed":
                console.print(str(++i) + ") " + check.reason)
        raise typer.Exit(code=1)


def _print_table(run):
    table = Table(box=box.ROUNDED)
    table.add_column("Result", no_wrap=True)
    table.add_column("Check", max_width=100)
    table.add_column("Field", max_width=32)
    table.add_column("Details", max_width=50)
    for check in run.checks:
        table.add_row(with_markup(check.result), check.name, to_field(run, check), check.reason)
    console.print(table)


def to_field(run, check):
    models = [c.model for c in run.checks]
    if len(set(models)) > 1:
        if check.field is None:
            return check.model
        return check.model + "." + check.field
    else:
        return check.field


def _print_logs(run):
    console.print("\nLogs:")
    for log in run.logs:
        console.print(log.timestamp.strftime("%y-%m-%d %H:%M:%S"), log.level.ljust(5), log.message)


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
