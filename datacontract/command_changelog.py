import typer
from typing_extensions import Annotated

from datacontract.cli import app, console, debug_option, enable_debug_logging
from datacontract.data_contract import DataContract
from datacontract.output.text_changelog_results import write_text_changelog_results


@app.command(
    name="changelog",
    epilog="Example: datacontract changelog datacontract-v1.yaml datacontract-v2.yaml",
)
def changelog(
    v1: Annotated[str, typer.Argument(help="The location (url or path) of the source (before) data contract YAML.")],
    v2: Annotated[str, typer.Argument(help="The location (url or path) of the target (after) data contract YAML.")],
    inline_references: Annotated[
        bool,
        typer.Option(
            help="Resolve external references in the contract and inline the fetched content "
            "from the configured entropy-data host (currently: authoritativeDefinitions[type=definition])."
        ),
    ] = True,
    debug: debug_option = None,
):
    """Show a changelog between two data contracts."""
    enable_debug_logging(debug)
    result = DataContract(data_contract_file=v1, inline_references=inline_references).changelog(
        DataContract(data_contract_file=v2, inline_references=inline_references)
    )
    write_text_changelog_results(result, console)
