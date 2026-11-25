from enum import Enum

import typer
import yaml
from typing_extensions import Annotated

from datacontract.cli import app, console, debug_option, enable_debug_logging, inline_references_option
from datacontract.config import cli_config
from datacontract.data_contract import DataContract
from datacontract.model.breaking import Perspective
from datacontract.output.text_breaking_results import write_text_breaking_results


class BreakingOutputFormat(str, Enum):
    text = "text"
    json = "json"
    yaml = "yaml"


@app.command(
    name="breaking",
    epilog="Example: datacontract breaking datacontract-v1.yaml datacontract-v2.yaml",
)
def breaking(
    v1: Annotated[
        str,
        typer.Argument(help="The location (url, s3 url, or local path) of the source (before) data contract YAML."),
    ],
    v2: Annotated[
        str,
        typer.Argument(help="The location (url, s3 url, or local path) of the target (after) data contract YAML."),
    ],
    perspective: Annotated[
        Perspective,
        typer.Option(
            help="`consumer` flags changes that lead to unexpected data for consumers, `producer` flags changes that can make data contract tests fail."
        ),
    ] = Perspective.CONSUMER,
    inline_references: inline_references_option = True,
    output_format: Annotated[
        BreakingOutputFormat,
        typer.Option(
            help="Output format. Accepted values: text, json, yaml. Use json or yaml to process breaking changes with other tools."
        ),
    ] = BreakingOutputFormat.text,
    debug: debug_option = None,
):
    """Show compatibility impact between two data contracts."""
    enable_debug_logging(debug)
    result = DataContract(config=cli_config(), data_contract_file=v1, inline_references=inline_references).breaking(
        DataContract(config=cli_config(), data_contract_file=v2, inline_references=inline_references),
        perspective=perspective,
    )
    if output_format == BreakingOutputFormat.json:
        typer.echo(result.pretty())
    elif output_format == BreakingOutputFormat.yaml:
        typer.echo(yaml.safe_dump(result.model_dump(mode="json"), sort_keys=False, allow_unicode=True), nl=False)
    else:
        write_text_breaking_results(result, console)
    if result.is_breaking:
        raise typer.Exit(code=1)
