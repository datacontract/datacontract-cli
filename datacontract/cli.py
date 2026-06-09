import logging
import os
import sys
from importlib import metadata
from pathlib import Path
from typing import Iterable, Optional

import typer
from click import Context
from dotenv import find_dotenv, load_dotenv
from rich.console import Console
from typer.core import TyperGroup
from typing_extensions import Annotated

from datacontract.output.output_format import OutputFormat

console = Console()

debug_option = Annotated[bool, typer.Option(help="Enable debug logging")]


# Order in which top-level commands appear in `datacontract --help` (cf. README.md)
COMMAND_ORDER = [
    "init",
    "lint",
    "changelog",
    "test",
    "ci",
    "export",
    "dbt",
    "import",
    "catalog",
    "publish",
    "api",
]


class OrderedCommands(TyperGroup):
    def list_commands(self, ctx: Context) -> Iterable[str]:
        known = set(COMMAND_ORDER)
        # Trailing fallback keeps any future command visible even if COMMAND_ORDER forgets it.
        return [c for c in COMMAND_ORDER if c in self.commands] + [c for c in self.commands if c not in known]


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
        positionals = [a for a in args if isinstance(a, str) and not a.startswith("-")]
        subcommand = positionals[0] if positionals else None

        # this function is called by both `datacontract` and `datacontract import`
        is_import_snowflake = (positionals[:1] == ["snowflake"]) or (positionals[:2] == ["import", "snowflake"])

        rewritten_args = []
        for arg in args:
            if isinstance(arg, str) and arg.startswith("--"):
                flag, _, value = arg.partition("=")
                if flag == "--schema" and not is_import_snowflake:
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
    # Load environment variables (e.g., credentials) from a .env file in the
    # current working directory, walking up parent directories until one is found.
    # Already-set environment variables take precedence.
    load_dotenv(dotenv_path=find_dotenv(usecwd=True), override=False)


def enable_debug_logging(debug: bool, otherwise_disable_stderr: bool = False):
    if not debug and otherwise_disable_stderr:
        # some commands render run.logs to the console themselves; a NullHandler keeps
        # the mirrored stdlib WARNING/ERROR (Run.log_*) off stderr so it isn't shown twice.
        logging.basicConfig(handlers=[logging.NullHandler()], force=True)
        return

    logging.basicConfig(
        level=logging.DEBUG if debug else logging.WARNING,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stderr,
        force=True,
    )

    if not debug:
        # Keep noisy third-party loggers quiet
        for noisy_logger in ("snowflake.connector", "py4j", "pyspark", "urllib3", "ibis"):
            logging.getLogger(noisy_logger).setLevel(logging.ERROR)


def validate_publish_url(publish: str | None) -> None:
    """Reject `--publish` values that aren't http/https before any real work runs."""
    if publish is not None and not (publish.startswith("http://") or publish.startswith("https://")):
        console.print(f"[red]--publish URL must start with http:// or https:// (got: {publish!r}).[/red]")
        raise typer.Exit(code=1)


def resolve_output_format(output_format: Optional[OutputFormat], output: Optional[Path]) -> Optional[OutputFormat]:
    if output_format is not None or output is None:
        return output_format

    inferred = OutputFormat.infer_from_output_path(output)
    if inferred is None:
        detail = f" from extension '{output.suffix}'" if output.suffix else ""
        console.print(f"Error: Cannot infer output format{detail}. Please specify --output-format (json or junit).")
        raise typer.Exit(code=1)

    return inferred


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
# Display order for `--help` is controlled by COMMAND_ORDER above, not by import order.
from datacontract import (  # noqa: E402, F401
    command_api,
    command_catalog,
    command_changelog,
    command_ci,
    command_dbt,
    command_export,
    command_import,
    command_init,
    command_lint,
    command_publish,
    command_test,
)

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
app.add_typer(
    command_dbt.dbt_app,
    name="dbt",
    help="Work with data contracts in your dbt project.",
    epilog="Example: datacontract dbt sync orders.odcs.yaml --project-dir ./warehouse",
)


def main():
    try:
        app()
    except Exception as e:
        # If an uncaught exception occurs, only print its name (except when debug mode is enabled)
        if "--debug" in sys.argv or os.environ.get("DATACONTRACT_CLI_DEBUG") == "1":
            raise
        from datacontract.model.exceptions import DataContractException

        message = e.reason if isinstance(e, DataContractException) else str(e)
        console.print(f"[red]Error:[/red] {message}")
        console.print("[dim]Pass --debug (or set DATACONTRACT_CLI_DEBUG=1) for the full traceback.[/dim]")
        sys.exit(1)


if __name__ == "__main__":
    main()
