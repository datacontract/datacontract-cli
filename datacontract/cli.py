import logging
import os
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

    RENAMED_FLAGS = {
        "--format": None,
        "--rdf-base": "--base",
        "--sql-server-type": "--dialect",
        "--bigquery-project": "--project",
        "--bigquery-dataset": "--dataset",
        "--bigquery-table": "--table",
        "--unity-table-full-name": "--table",
        "--dbt-model": "--model",
        "--glue-table": "--table",
        "--iceberg-table": "--table",
    }

    def parse_args(self, ctx: Context, args):
        # First positional argument
        subcommand = next((a for a in args if isinstance(a, str) and not a.startswith("-")), None)

        rewritten_args = []
        for arg in args:
            if isinstance(arg, str) and arg.startswith("--"):
                flag, _, value = arg.partition("=")
                if flag == "--schema":
                    typer.secho(
                        "Warning: --schema was replaced with --json-schema in v0.12.0 and will be removed in v0.13.0.",
                        err=True,
                        fg=typer.colors.YELLOW,
                    )
                    rewritten_args.append(f"--json-schema={value}" if value else "--json-schema")
                    continue
                if flag in self.RENAMED_FLAGS:
                    new_flag = self.RENAMED_FLAGS[flag]
                elif flag == "--source" and subcommand == "glue":
                    new_flag = "--database"
                elif flag == "--source" and subcommand == "spark":
                    new_flag = "--tables"
                else:
                    rewritten_args.append(arg)
                    continue
                change = "needs to be omitted since" if new_flag is None else f"was replaced with {new_flag} in"
                ctx.fail(
                    f"{flag} {change} v0.12.0 of datacontract-cli. "
                    f"See https://github.com/datacontract/datacontract-cli/releases/tag/v0.12.0"
                )
            rewritten_args.append(arg)
        return super().parse_args(ctx, rewritten_args)


app = typer.Typer(
    cls=OrderedCommandsWithMigrationHints,
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
    epilog=(
        "Example: datacontract export html datacontract.yaml --output datacontract.html\n\n"
        "For SQL dialects (postgres, mysql, snowflake, databricks, sqlserver, trino, oracle), "
        "use `datacontract export sql --dialect <dialect>`."
    ),
)


def main():
    try:
        app()
    except Exception as e:
        # If an uncaught exception occurs, only print its name (except when debug mode is enabled)
        if "--debug" in sys.argv or os.environ.get("DATACONTRACT_CLI_DEBUG") == "1":
            raise
        console.print(f"[red]Error:[/red] {e}")
        console.print("[dim]Pass --debug (or set DATACONTRACT_CLI_DEBUG=1) for the full traceback.[/dim]")
        sys.exit(1)


if __name__ == "__main__":
    main()
