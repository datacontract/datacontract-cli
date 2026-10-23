from pathlib import Path
from typing import Optional

import typer
from typing_extensions import Annotated

from datacontract.catalog.catalog import create_data_contract_page, create_index_html, create_index_md
from datacontract.cli import app, console, debug_option, enable_debug_logging
from datacontract.model.exceptions import DataContractException


@app.command(
    name="catalog",
    epilog='Example: datacontract catalog --files "**/*.yaml" --output catalog/',
)
def catalog(
    files: Annotated[
        Optional[str],
        typer.Option(
            help="Glob pattern for the data contract files to include in the catalog. Applies recursively to any subfolders."
        ),
    ] = "*.yaml",
    output: Annotated[Optional[str], typer.Option(help="Output directory for the catalog files.")] = "catalog/",
    markdown: Annotated[
        bool,
        typer.Option("--markdown", help="Create Markdown files with an index.md instead of HTML pages."),
    ] = False,
    mermaid: Annotated[
        bool,
        typer.Option("--mermaid", help="Add a Mermaid entity relationship diagram to each page. Requires --markdown."),
    ] = False,
    schema: Annotated[
        str,
        typer.Option("--json-schema", help="The location (url or path) of the ODCS JSON Schema"),
    ] = None,
    debug: debug_option = None,
):
    """
    Create a catalog of data contracts, as HTML or Markdown.
    """
    enable_debug_logging(debug)
    if mermaid and not markdown:
        raise typer.BadParameter("--mermaid requires --markdown (the HTML pages always include the diagram).")

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
            create_data_contract_page(contracts, file, path, schema, "markdown" if markdown else "html", mermaid)
        except DataContractException as e:
            if e.reason == "Cannot parse ODPS product":
                console.print(f"Skipped {file} due to error: {e.reason}")
            else:
                console.print(f"Skipped {file} due to error: {e}")
        except Exception as e:
            console.print(f"Skipped {file} due to error: {e}")

    if markdown:
        create_index_md(contracts, path)
    else:
        create_index_html(contracts, path)
