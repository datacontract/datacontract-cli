import typer
from typing_extensions import Annotated

from datacontract.cli import app, console, debug_option, enable_debug_logging
from datacontract.config import cli_config
from datacontract.data_contract import DataContract
from datacontract.output.text_breaking_results import write_text_breaking_results


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
    inline_references: Annotated[
        bool,
        typer.Option(
            help="Resolve external references (currently: authoritativeDefinitions\\[type in {definition, semantics}]) "
            "in the contract and inline the fetched content from the configured entropy-data host."
        ),
    ] = True,
    debug: debug_option = None,
):
    """Show compatibility impact between two data contracts."""
    enable_debug_logging(debug)
    result = DataContract(config=cli_config(), data_contract_file=v1, inline_references=inline_references).breaking(
        DataContract(config=cli_config(), data_contract_file=v2, inline_references=inline_references)
    )
    write_text_breaking_results(result, console)
    if result.is_breaking:
        raise typer.Exit(code=1)
