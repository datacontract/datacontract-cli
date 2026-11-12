from enum import Enum

import typer
import yaml
from typing_extensions import Annotated

from datacontract.cli import app, console, debug_option, enable_debug_logging, inline_references_option
from datacontract.config import cli_config
from datacontract.data_contract import DataContract
from datacontract.output.text_changelog_results import write_text_changelog_results


class ChangelogOutputFormat(str, Enum):
    text = "text"
    json = "json"
    yaml = "yaml"


@app.command(
    name="changelog",
    epilog="Example: datacontract changelog datacontract-v1.yaml datacontract-v2.yaml",
)
def changelog(
    v1: Annotated[
        str,
        typer.Argument(help="The location (url, s3 url, or local path) of the source (before) data contract YAML."),
    ],
    v2: Annotated[
        str,
        typer.Argument(help="The location (url, s3 url, or local path) of the target (after) data contract YAML."),
    ],
    inline_references: inline_references_option = True,
    output_format: Annotated[
        ChangelogOutputFormat,
        typer.Option(
            help="Output format. Accepted values: text, json, yaml. Use json or yaml to process the changelog with other tools."
        ),
    ] = ChangelogOutputFormat.text,
    debug: debug_option = None,
):
    """Show a changelog between two data contracts."""
    enable_debug_logging(debug)
    result = DataContract(config=cli_config(), data_contract_file=v1, inline_references=inline_references).changelog(
        DataContract(config=cli_config(), data_contract_file=v2, inline_references=inline_references)
    )
    if output_format == ChangelogOutputFormat.json:
        typer.echo(result.pretty())
    elif output_format == ChangelogOutputFormat.yaml:
        typer.echo(yaml.safe_dump(result.model_dump(mode="json"), sort_keys=False, allow_unicode=True), nl=False)
    else:
        write_text_changelog_results(result, console)
