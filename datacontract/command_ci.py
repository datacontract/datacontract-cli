from enum import Enum
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from typing_extensions import Annotated

from datacontract.cli import _print_logs, app, console, debug_option, enable_debug_logging
from datacontract.data_contract import DataContract
from datacontract.output.ci_output import write_ci_output, write_ci_summary, write_json_results
from datacontract.output.output_format import OutputFormat
from datacontract.output.test_results_writer import write_test_result


class FailOn(str, Enum):
    warning = "warning"
    error = "error"
    never = "never"


@app.command(
    name="ci",
    epilog="Example: datacontract ci datacontract.yaml --output test-results.xml --output-format junit",
)
def ci(
    locations: Annotated[
        Optional[list[str]],
        typer.Argument(help="The location(s) (url or path) of the data contract yaml file(s)."),
    ] = None,
    schema: Annotated[
        str,
        typer.Option("--json-schema", help="The location (url or path) of the ODCS JSON Schema"),
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
        FailOn,
        typer.Option(help="Minimum severity that causes a non-zero exit code."),
    ] = FailOn.error,
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
