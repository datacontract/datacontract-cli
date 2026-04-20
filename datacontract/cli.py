import logging
import sys
from importlib import metadata
from typing import Iterable

import typer
from click import Context
from rich.console import Console
from typer.core import TyperGroup
from typing_extensions import Annotated

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


def enable_debug_logging(debug: bool):
    if debug:
        logging.basicConfig(
            level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", stream=sys.stderr
        )


def _print_logs(run, out=None):
    if out is None:
        out = console
    out.print("\nLogs:")
    for log in run.logs:
        out.print(log.timestamp.strftime("%y-%m-%d %H:%M:%S"), log.level.ljust(5), log.message)


# ---------------------------------------------------------------------------
# Register commands (must be after app and shared helpers are defined so the
# command_* modules can import from this module without circular-import issues)
# ---------------------------------------------------------------------------
from datacontract import (  # noqa: E402, F401
    command_api,
    command_catalog,
    command_changelog,
    command_ci,
    command_export,
    command_import,
    command_init,
    command_lint,
    command_publish,
    command_test,
)

# Commands with subcommands
app.add_typer(
    command_import.import_app,
    name="import",
    help="Create a data contract from a source format.",
    epilog="Example: datacontract import sql --source ddl.sql --dialect postgres --output datacontract.yaml",
)
app.add_typer(
    command_export.export_app,
    name="export",
    help="Convert a data contract to a target format.",
    epilog="Example: datacontract export html datacontract.yaml --output datacontract.html",
)

if __name__ == "__main__":
    app()
