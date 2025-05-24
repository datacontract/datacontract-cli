import os
from importlib import metadata
from pathlib import Path
from typing import Iterable, List, Optional

import typer
from click import Context
from rich.console import Console
from typer.core import TyperGroup
from typing_extensions import Annotated

from datacontract.catalog.catalog import create_data_contract_html, create_index_html
from datacontract.data_contract import DataContract, ExportFormat
from datacontract.imports.importer import ImportFormat
from datacontract.init.init_template import get_init_template
from datacontract.integration.datamesh_manager import (
    publish_data_contract_to_datamesh_manager,
)
from datacontract.lint.resolve import resolve_data_contract_dict
from datacontract.output.output_format import OutputFormat
from datacontract.output.test_results_writer import write_test_result

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
        None,
        "--version",
        help="Prints the current version.",
        callback=version_callback,
        is_eager=True,
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
        str, typer.Argument(help="The location of the data contract file to create.")
    ] = "datacontract.yaml",
    template: Annotated[str, typer.Option(help="URL of a template or data contract")] = None,
    overwrite: Annotated[bool, typer.Option(help="Replace the existing datacontract.yaml")] = False,
):
    """
    Create an empty data contract.
    """
    if not overwrite and os.path.exists(location):
        console.print("File already exists, use --overwrite to overwrite")
        raise typer.Exit(code=1)
    template_str = get_init_template(template)
    with open(location, "w") as f:
        f.write(template_str)
    console.print("📄 data contract written to " + location)


@app.command()
def lint(
    location: Annotated[
        str,
        typer.Argument(help="The location (url or path) of the data contract yaml."),
    ] = "datacontract.yaml",
    schema: Annotated[
        str,
        typer.Option(help="The location (url or path) of the Data Contract Specification JSON Schema"),
    ] = None,
    output: Annotated[
        Path,
        typer.Option(
            help="Specify the file path where the test results should be written to (e.g., './test-results/TEST-datacontract.xml'). If no path is provided, the output will be printed to stdout."
        ),
    ] = None,
    output_format: Annotated[OutputFormat, typer.Option(help="The target format for the test results.")] = None,
):
    """
    Validate that the datacontract.yaml is correctly formatted.
    """
    run = DataContract(data_contract_file=location, schema_location=schema).lint()
    write_test_result(run, console, output_format, output)


@app.command()
def test(
    location: Annotated[
        str,
        typer.Argument(help="The location (url or path) of the data contract yaml."),
    ] = "datacontract.yaml",
    schema: Annotated[
        str,
        typer.Option(help="The location (url or path) of the Data Contract Specification JSON Schema"),
    ] = None,
    server: Annotated[
        str,
        typer.Option(
            help="The server configuration to run the schema and quality tests. "
            "Use the key of the server object in the data contract yaml file "
            "to refer to a server, e.g., `production`, or `all` for all "
            "servers (default)."
        ),
    ] = "all",
    publish: Annotated[str, typer.Option(help="The url to publish the results after the test")] = None,
    output: Annotated[
        Path,
        typer.Option(
            help="Specify the file path where the test results should be written to (e.g., './test-results/TEST-datacontract.xml')."
        ),
    ] = None,
    output_format: Annotated[OutputFormat, typer.Option(help="The target format for the test results.")] = None,
    logs: Annotated[bool, typer.Option(help="Print logs")] = False,
    ssl_verification: Annotated[
        bool,
        typer.Option(help="SSL verification when publishing the data contract."),
    ] = True,
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
        server=server,
        ssl_verification=ssl_verification,
    ).test()
    if logs:
        _print_logs(run)
    write_test_result(run, console, output_format, output)


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
        typer.Option(
            help="[rdf] The base URI used to generate the RDF graph.",
            rich_help_panel="RDF Options",
        ),
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
        str,
        typer.Argument(help="The location (url or path) of the data contract yaml."),
    ] = "datacontract.yaml",
    schema: Annotated[
        str,
        typer.Option(help="The location (url or path) of the Data Contract Specification JSON Schema"),
    ] = None,
    # TODO: this should be a subcommand
    engine: Annotated[
        Optional[str],
        typer.Option(help="[engine] The engine used for great expection run."),
    ] = None,
    # TODO: this should be a subcommand
    template: Annotated[
        Optional[Path],
        typer.Option(help="[custom] The file path of Jinja template."),
    ] = None,
):
    """
    Convert data contract to a specific format. Saves to file specified by `output` option if present, otherwise prints to stdout.
    """
    # TODO exception handling
    result = DataContract(data_contract_file=location, schema_location=schema, server=server).export(
        export_format=format,
        model=model,
        server=server,
        rdf_base=rdf_base,
        sql_server_type=sql_server_type,
        engine=engine,
        template=template,
    )
    # Don't interpret console markup in output.
    if output is None:
        console.print(result, markup=False, soft_wrap=True)
    else:
        with output.open(mode="w", encoding="utf-8") as f:
            f.write(result)
        console.print(f"Written result to {output}")


@app.command(name="import")
def import_(
    format: Annotated[ImportFormat, typer.Option(help="The format of the source file.")],
    output: Annotated[
        Path,
        typer.Option(
            help="Specify the file path where the Data Contract will be saved. If no path is provided, the output will be printed to stdout."
        ),
    ] = None,
    source: Annotated[
        Optional[str],
        typer.Option(help="The path to the file that should be imported."),
    ] = None,
    dialect: Annotated[
        Optional[str],
        typer.Option(help="The SQL dialect to use when importing SQL files, e.g., postgres, tsql, bigquery."),
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
    iceberg_table: Annotated[
        Optional[str],
        typer.Option(help="Table name to assign to the model created from the Iceberg schema."),
    ] = None,
    template: Annotated[
        Optional[str],
        typer.Option(help="The location (url or path) of the Data Contract Specification Template"),
    ] = None,
    schema: Annotated[
        str,
        typer.Option(help="The location (url or path) of the Data Contract Specification JSON Schema"),
    ] = None,
    owner: Annotated[
        Optional[str],
        typer.Option(help="The owner or team responsible for managing the data contract."),
    ] = None,
    id: Annotated[
        Optional[str],
        typer.Option(help="The identifier for the the data contract."),
    ] = None,
):
    """
    Create a data contract from the given source location. Saves to file specified by `output` option if present, otherwise prints to stdout.
    """
    result = DataContract().import_from_source(
        format=format,
        source=source,
        template=template,
        schema=schema,
        dialect=dialect,
        glue_table=glue_table,
        bigquery_table=bigquery_table,
        bigquery_project=bigquery_project,
        bigquery_dataset=bigquery_dataset,
        unity_table_full_name=unity_table_full_name,
        dbt_model=dbt_model,
        dbml_schema=dbml_schema,
        dbml_table=dbml_table,
        iceberg_table=iceberg_table,
        owner=owner,
        id=id,
    )
    if output is None:
        console.print(result.to_yaml(), markup=False, soft_wrap=True)
    else:
        with output.open(mode="w", encoding="utf-8") as f:
            f.write(result.to_yaml())
        console.print(f"Written result to {output}")


@app.command(name="publish")
def publish(
    location: Annotated[
        str,
        typer.Argument(help="The location (url or path) of the data contract yaml."),
    ] = "datacontract.yaml",
    schema: Annotated[
        str,
        typer.Option(help="The location (url or path) of the Data Contract Specification JSON Schema"),
    ] = None,
    ssl_verification: Annotated[
        bool,
        typer.Option(help="SSL verification when publishing the data contract."),
    ] = True,
):
    """
    Publish the data contract to the Data Mesh Manager.
    """
    publish_data_contract_to_datamesh_manager(
        data_contract_dict=resolve_data_contract_dict(location),
        ssl_verification=ssl_verification,
    )


@app.command(name="catalog")
def catalog(
    files: Annotated[
        Optional[str],
        typer.Option(
            help="Glob pattern for the data contract files to include in the catalog. Applies recursively to any subfolders."
        ),
    ] = "*.yaml",
    output: Annotated[Optional[str], typer.Option(help="Output directory for the catalog html files.")] = "catalog/",
    schema: Annotated[
        str,
        typer.Option(help="The location (url or path) of the Data Contract Specification JSON Schema"),
    ] = None,
):
    """
    Create a html catalog of data contracts.
    """
    path = Path(output)
    path.mkdir(parents=True, exist_ok=True)
    console.print(f"Created {output}")

    contracts = []
    for file in Path().rglob(files):
        try:
            create_data_contract_html(contracts, file, path, schema)
        except Exception as e:
            console.print(f"Skipped {file} due to error: {e}")

    create_index_html(contracts, path)


@app.command()
def breaking(
    location_old: Annotated[
        str,
        typer.Argument(help="The location (url or path) of the old data contract yaml."),
    ],
    location_new: Annotated[
        str,
        typer.Argument(help="The location (url or path) of the new data contract yaml."),
    ],
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
    location_old: Annotated[
        str,
        typer.Argument(help="The location (url or path) of the old data contract yaml."),
    ],
    location_new: Annotated[
        str,
        typer.Argument(help="The location (url or path) of the new data contract yaml."),
    ],
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
    location_old: Annotated[
        str,
        typer.Argument(help="The location (url or path) of the old data contract yaml."),
    ],
    location_new: Annotated[
        str,
        typer.Argument(help="The location (url or path) of the new data contract yaml."),
    ],
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
def api(
    port: Annotated[int, typer.Option(help="Bind socket to this port.")] = 4242,
    host: Annotated[
        str, typer.Option(help="Bind socket to this host. Hint: For running in docker, set it to 0.0.0.0")
    ] = "127.0.0.1",
):
    """
    Start the datacontract CLI as server application with REST API.

    The OpenAPI documentation as Swagger UI is available on http://localhost:4242.
    You can execute the commands directly from the Swagger UI.

    To protect the API, you can set the environment variable DATACONTRACT_CLI_API_KEY to a secret API key.
    To authenticate, requests must include the header 'x-api-key' with the correct API key.
    This is highly recommended, as data contract tests may be subject to SQL injections or leak sensitive information.

    To connect to servers (such as a Snowflake data source), set the credentials as environment variables as documented in
    https://cli.datacontract.com/#test
    """
    import uvicorn
    from uvicorn.config import LOGGING_CONFIG

    log_config = LOGGING_CONFIG
    log_config["root"] = {"level": "INFO"}

    uvicorn.run(app="datacontract.api:app", port=port, host=host, reload=True, log_config=LOGGING_CONFIG)


def _print_logs(run):
    console.print("\nLogs:")
    for log in run.logs:
        console.print(log.timestamp.strftime("%y-%m-%d %H:%M:%S"), log.level.ljust(5), log.message)


if __name__ == "__main__":
    app()
