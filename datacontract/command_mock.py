from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from typing_extensions import Annotated

from datacontract.cli import app, debug_option, enable_debug_logging
from datacontract.config import cli_config
from datacontract.data_contract import DataContract

console = Console()


@app.command(
    name="mock",
    epilog="Example: datacontract mock datacontract.yaml --rows 25 --output ./mock-data",
)
def mock(
    location: Annotated[
        str,
        typer.Argument(help="The location (url, s3 url, or local path) of the data contract yaml."),
    ] = "datacontract.yaml",
    schema_name: Annotated[
        str,
        typer.Option(
            help="Which schema to generate mock data for, e.g., `orders`, or `all` for all schemas (default)."
        ),
    ] = "all",
    server: Annotated[
        Optional[str],
        typer.Option(
            help="The server to use to resolve the output format for `physicalType: file` schemas "
            "(its `format`, e.g., json/csv/parquet). Defaults to the first server declaring a format, "
            "or the first server."
        ),
    ] = None,
    rows: Annotated[int, typer.Option(help="Number of mock records to generate per schema.")] = 10,
    output: Annotated[
        Optional[Path],
        typer.Option(help="Directory to write the generated files to. Defaults to the current directory."),
    ] = None,
    seed: Annotated[
        Optional[int],
        typer.Option(help="Seed for the random generator, for reproducible mock data."),
    ] = None,
    locale: Annotated[
        str,
        typer.Option(
            help="Language used to generate fake data: FR (français), EN (English, default), "
            "ES (Español), DE (Deutsch), NL (Nederlands), IT (Italiano), PT (Português), ZH (中文)."
        ),
    ] = "EN",
    debug: debug_option = None,
):
    """Generate fake datasets from a data contract using mimesis.

    For each schema, `physicalType: table` renders SQL INSERT statements from a Jinja
    template; `physicalType: file` renders json, csv, or parquet, picked from the
    resolved server's `format`. ODCS `relationships` (foreign keys) are honored: a
    referenced schema is generated before the schema referencing it, and the
    referencing column samples an actual generated value instead of an unrelated one.
    Integer primary keys are treated as identity/auto-increment columns and get the
    directive their server `type` needs to accept explicit values (`SET IDENTITY_INSERT`
    for sqlserver, `OVERRIDING SYSTEM VALUE` for postgres/oracle, plain INSERT otherwise).
    """
    enable_debug_logging(debug)

    results = DataContract(
        config=cli_config(),
        data_contract_file=location,
        server=server,
    ).mock(
        schema_name=schema_name,
        rows=rows,
        seed=seed,
        locale=locale,
    )

    output_dir = output or Path(".")
    output_dir.mkdir(parents=True, exist_ok=True)

    summary = Table()
    summary.add_column("Schema")
    summary.add_column("Physical Type")
    summary.add_column("Format")
    summary.add_column("File")

    for result in results:
        destination = output_dir / result.suggested_filename
        mode = "wb" if isinstance(result.content, bytes) else "w"
        encoding = None if mode == "wb" else "utf-8"
        with destination.open(mode=mode, encoding=encoding) as f:
            f.write(result.content)
        summary.add_row(result.schema_name, result.physical_type, result.format, str(destination))

    console.print(summary)
