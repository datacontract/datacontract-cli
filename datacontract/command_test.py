from pathlib import Path

import typer
from typing_extensions import Annotated

from datacontract.cli import _print_logs, app, console, debug_option, enable_debug_logging
from datacontract.data_contract import DataContract
from datacontract.lint.resolve import resolve_data_contract
from datacontract.output.output_format import OutputFormat
from datacontract.output.test_results_writer import write_test_result


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
