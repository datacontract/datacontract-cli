import logging
import os
import sys
from importlib import metadata
from pathlib import Path
from typing import Iterable, Optional

import click
import typer
from click import Context
from rich.console import Console
from typer.core import TyperGroup
from typing_extensions import Annotated

from datacontract.catalog.catalog import create_data_contract_html, create_index_html
from datacontract.data_contract import DataContract
from datacontract.init.init_template import get_init_template
from datacontract.integration.entropy_data import (
    publish_data_contract_to_entropy_data,
)
from datacontract.lint.resolve import resolve_data_contract, resolve_data_contract_dict
from datacontract.model.exceptions import DataContractException
from datacontract.output.ci_output import write_ci_output, write_ci_summary, write_json_results
from datacontract.output.output_format import OutputFormat
from datacontract.output.test_results_writer import write_test_result
from datacontract.output.text_changelog_results import write_text_changelog_results

console = Console()

debug_option = Annotated[bool, typer.Option(help="Enable debug logging")]


class OrderedCommands(TyperGroup):
    def list_commands(self, ctx: Context) -> Iterable[str]:
        return self.commands.keys()


class OrderedCommandsWithMigrationHints(OrderedCommands):
    """Intercepts removed or renamed options on import/export and points the user to the v0.12.0 migration notes."""

    RENAMED_FLAGS = frozenset(
        {
            "--format",
            "--rdf-base",
            "--sql-server-type",
            "--bigquery-project",
            "--bigquery-dataset",
            "--bigquery-table",
            "--unity-table-full-name",
            "--dbt-model",
            "--dbml-schema",
            "--dbml-table",
            "--glue-table",
            "--iceberg-table",
        }
    )

    def parse_args(self, ctx: Context, args):
        first_positional_arg = next((a for a in args if isinstance(a, str) and not a.startswith("-")), None)
        for arg in args:
            if isinstance(arg, str) and arg.startswith("--"):
                flag = arg.split("=", 1)[0]
                is_renamed = (
                    flag in self.RENAMED_FLAGS
                    or (flag == "--schema" and first_positional_arg != "dbml")
                    or (flag == "--source" and first_positional_arg in ("glue", "spark"))
                )
                if is_renamed:
                    ctx.fail(
                        f"{flag} was removed in v0.12.0 of datacontract-cli. See https://github.com/datacontract/datacontract-cli/releases/tag/v0.12.0"
                    )
        return super().parse_args(ctx, args)


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
    and export to different formats.
    """
    pass


@app.command(name="init")
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


@app.command(name="lint")
def lint(
    location: Annotated[
        str,
        typer.Argument(help="The location (url or path) of the data contract yaml."),
    ] = "datacontract.yaml",
    schema: Annotated[
        str,
        typer.Option("--odcs-schema", help="The location (url or path) of the ODCS JSON Schema"),
    ] = None,
    output: Annotated[
        Path,
        typer.Option(
            help="Specify the file path where the test results should be written to (e.g., './test-results/TEST-datacontract.xml'). If no path is provided, the output will be printed to stdout."
        ),
    ] = None,
    output_format: Annotated[OutputFormat, typer.Option(help="The target format for the test results.")] = None,
    all_errors: Annotated[
        bool,
        typer.Option(
            "--all-errors",
            help="Report all JSON Schema validation errors instead of stopping after the first one.",
        ),
    ] = False,
    debug: debug_option = None,
):
    """
    Validate that the datacontract.yaml is correctly formatted.
    """
    enable_debug_logging(debug)

    run = DataContract(data_contract_file=location, schema_location=schema, all_errors=all_errors).lint()
    write_test_result(run, console, output_format, output)


def enable_debug_logging(debug: bool):
    if debug:
        logging.basicConfig(
            level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", stream=sys.stderr
        )


@app.command(name="changelog")
def changelog(
    v1: Annotated[str, typer.Argument(help="The location (path) of the source (before) data contract YAML.")],
    v2: Annotated[str, typer.Argument(help="The location (path) of the target (after) data contract YAML.")],
    debug: debug_option = None,
):
    """Show a changelog between two data contracts."""
    enable_debug_logging(debug)
    result = DataContract(data_contract_file=v1).changelog(DataContract(data_contract_file=v2))
    write_text_changelog_results(result, console)


@app.command(name="test")
def test(
    location: Annotated[
        str,
        typer.Argument(help="The location (url or path) of the data contract yaml."),
    ] = "datacontract.yaml",
    schema: Annotated[
        str,
        typer.Option("--odcs-schema", help="The location (url or path) of the ODCS JSON Schema"),
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
    schema_name: Annotated[
        str,
        typer.Option(help="Which schema to test, e.g., `orders`, or `all` for all schemas (default)."),
    ] = "all",
    publish_test_results: Annotated[
        bool, typer.Option(help="Deprecated. Use publish parameter. Publish the results after the test")
    ] = False,
    publish: Annotated[str, typer.Option(help="The url to publish the results after the test.")] = None,
    output: Annotated[
        Path,
        typer.Option(
            help="Specify the file path where the test results should be written to (e.g., './test-results/TEST-datacontract.xml')."
        ),
    ] = None,
    output_format: Annotated[OutputFormat, typer.Option(help="The target format for the test results.")] = None,
    checks: Annotated[
        str,
        typer.Option(
            help="Comma-separated list of check categories to run. "
            "Available categories: schema, quality, servicelevel, custom. "
            "Omit to enable all."
        ),
    ] = None,
    logs: Annotated[bool, typer.Option(help="Print logs")] = False,
    ssl_verification: Annotated[
        bool,
        typer.Option(help="SSL verification when publishing the data contract."),
    ] = True,
    debug: debug_option = None,
):
    """
    Run schema and quality tests on configured servers.
    """
    enable_debug_logging(debug)

    valid_categories = {"schema", "quality", "servicelevel", "custom"}
    check_categories = None
    if checks is not None:
        check_categories = {c.strip() for c in checks.split(",") if c.strip()}
        if not check_categories:
            console.print("[red]Empty --checks specified.[/red]")
            console.print(f"Available categories: {', '.join(sorted(valid_categories))}")
            raise typer.Exit(code=1)
        invalid = check_categories - valid_categories
        if invalid:
            console.print(f"[red]Invalid --checks specified: {', '.join(sorted(invalid))}[/red]")
            console.print(f"Available categories: {', '.join(sorted(valid_categories))}")
            raise typer.Exit(code=1)

    console.print(f"Testing {location}")
    if server == "all":
        server = None
    run = DataContract(
        data_contract_file=location,
        schema_location=schema,
        publish_test_results=publish_test_results,
        publish_url=publish,
        server=server,
        schema_name=schema_name,
        ssl_verification=ssl_verification,
        check_categories=check_categories,
    ).test()
    if logs:
        _print_logs(run)
    try:
        data_contract = resolve_data_contract(location, schema_location=schema)
    except Exception:
        data_contract = None
    write_test_result(run, console, output_format, output, data_contract)


@app.command(name="ci")
def ci(
    locations: Annotated[
        Optional[list[str]],
        typer.Argument(help="The location(s) (url or path) of the data contract yaml file(s)."),
    ] = None,
    schema: Annotated[
        str,
        typer.Option("--odcs-schema", help="The location (url or path) of the ODCS JSON Schema"),
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
    publish: Annotated[str, typer.Option(help="The url to publish the results after the test.")] = None,
    output: Annotated[
        Path,
        typer.Option(
            help="Specify the file path where the test results should be written to (e.g., './test-results/TEST-datacontract.xml')."
        ),
    ] = None,
    output_format: Annotated[OutputFormat, typer.Option(help="The target format for the test results.")] = None,
    logs: Annotated[bool, typer.Option(help="Print logs")] = False,
    json_output: Annotated[bool, typer.Option("--json", help="Print test results as JSON to stdout.")] = False,
    fail_on: Annotated[
        str,
        typer.Option(
            click_type=click.Choice(["warning", "error", "never"], case_sensitive=False),
            help="Minimum severity that causes a non-zero exit code.",
        ),
    ] = "error",
    ssl_verification: Annotated[
        bool,
        typer.Option(help="SSL verification when publishing the data contract."),
    ] = True,
    debug: debug_option = None,
):
    """
    Run tests for CI/CD pipelines. Emits GitHub Actions annotations and step summary.
    """
    enable_debug_logging(debug)

    if not locations:
        locations = ["datacontract.yaml"]

    if output and len(locations) > 1:
        console.print("Error: --output cannot be used with multiple contracts (results would overwrite each other).")
        raise typer.Exit(code=1)

    if server == "all":
        server = None

    # Plain text output for CI logs; --json sends human output to stderr.
    out = Console(stderr=True, no_color=True) if json_output else Console(no_color=True)

    results = []
    fail_results = {
        "warning": {"warning", "failed", "error"},
        "error": {"failed", "error"},
        "never": set(),
    }
    should_fail = False

    for location in locations:
        out.print(f"Testing {location}")
        run = DataContract(
            data_contract_file=location,
            schema_location=schema,
            publish_url=publish,
            server=server,
            ssl_verification=ssl_verification,
        ).test()
        if logs:
            _print_logs(run, out)
        results.append((location, run))
        write_ci_output(run, location, json_mode=json_output)
        try:
            write_test_result(run, out, output_format, output)
        except typer.Exit:
            pass
        if run.result in fail_results[fail_on]:
            should_fail = True

    write_ci_summary(results)
    if json_output:
        write_json_results(results)

    if should_fail:
        raise typer.Exit(code=1)


@app.command(name="publish")
def publish(
    location: Annotated[
        str,
        typer.Argument(help="The location (url or path) of the data contract yaml."),
    ] = "datacontract.yaml",
    schema: Annotated[
        str,
        typer.Option("--odcs-schema", help="The location (url or path) of the ODCS JSON Schema"),
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
        typer.Option("--odcs-schema", help="The location (url or path) of the ODCS JSON Schema"),
    ] = None,
    debug: debug_option = None,
):
    """
    Create a html catalog of data contracts.
    """
    enable_debug_logging(debug)

    path = Path(output)
    try:
        path.mkdir(parents=True, exist_ok=True)
    except FileExistsError:
        if not path.is_dir():
            raise
    console.print(f"Created {output}")

    contracts = []
    for file in Path().rglob(files):
        try:
            create_data_contract_html(contracts, file, path, schema)
        except DataContractException as e:
            if e.reason == "Cannot parse ODPS product":
                console.print(f"Skipped {file} due to error: {e.reason}")
            else:
                console.print(f"Skipped {file} due to error: {e}")
        except Exception as e:
            console.print(f"Skipped {file} due to error: {e}")

    create_index_html(contracts, path)


def _get_uvicorn_arguments(port: int, host: str, context: typer.Context) -> dict:
    """
    Take the default datacontract uvicorn arguments and merge them with the
    extra arguments passed to the command to start the API.
    """
    default_args = {
        "app": "datacontract.api:app",
        "port": port,
        "host": host,
        "reload": True,
    }

    # Create a list of the extra arguments, remove the leading -- from the cli arguments
    trimmed_keys = list(map(lambda x: str(x).replace("--", ""), context.args[::2]))
    # Merge the two dicts and return them as one dict
    return default_args | dict(zip(trimmed_keys, context.args[1::2]))


@app.command(name="api", context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def api(
    ctx: Annotated[typer.Context, typer.Option(help="Extra arguments to pass to uvicorn.run().")],
    port: Annotated[int, typer.Option(help="Bind socket to this port.")] = 4242,
    host: Annotated[
        str, typer.Option(help="Bind socket to this host. Hint: For running in docker, set it to 0.0.0.0")
    ] = "127.0.0.1",
    debug: debug_option = None,
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

    It is possible to run the API with extra arguments for `uvicorn.run()` as keyword arguments, e.g.:
    `datacontract api --port 1234 --root_path /datacontract`.
    """
    enable_debug_logging(debug)

    import uvicorn
    from uvicorn.config import LOGGING_CONFIG

    log_config = LOGGING_CONFIG
    log_config["root"] = {"level": "INFO"}

    uvicorn_args = _get_uvicorn_arguments(port, host, ctx)
    # Add the log config
    uvicorn_args["log_config"] = log_config
    # Run uvicorn
    uvicorn.run(**uvicorn_args)


def _print_logs(run, out=None):
    if out is None:
        out = console
    out.print("\nLogs:")
    for log in run.logs:
        out.print(log.timestamp.strftime("%y-%m-%d %H:%M:%S"), log.level.ljust(5), log.message)


# ---------------------------------------------------------------------------
# Register import/export sub-apps (must be after app is fully defined to
# avoid circular imports, since cli_import/cli_export import from this module)
# ---------------------------------------------------------------------------
from datacontract.cli_export import export_app  # noqa: E402
from datacontract.cli_import import import_app  # noqa: E402

app.add_typer(import_app, name="import", help="Create a data contract from a source format.")
app.add_typer(export_app, name="export", help="Convert a data contract to a target format.")


def main():
    try:
        app()
    except Exception as e:
        # If an uncaught exception occurs, only print its name (except when debug mode is enabled)
        if "--debug" in sys.argv or os.environ.get("DATACONTRACT_CLI_DEBUG") == "1":
            raise
        console.print(f"[red]Error:[/red] {e}")
        console.print("[dim]Pass --debug (or set DATACONTRACT_CLI_DEBUG=1) for the full traceback.[/dim]")
        sys.exit(1)


if __name__ == "__main__":
    main()
