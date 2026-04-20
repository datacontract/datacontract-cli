from pathlib import Path

import typer
from typing_extensions import Annotated

from datacontract.cli import app, console, debug_option, enable_debug_logging
from datacontract.data_contract import DataContract
from datacontract.output.output_format import OutputFormat
from datacontract.output.test_results_writer import write_test_result


@app.command(
    name="lint",
    epilog="Example: datacontract lint datacontract.yaml",
)
def lint(
    location: Annotated[
        str,
        typer.Argument(help="The location (url or path) of the data contract yaml."),
    ] = "datacontract.yaml",
    schema: Annotated[
        str,
        typer.Option("--json-schema", help="The location (url or path) of the ODCS JSON Schema"),
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
