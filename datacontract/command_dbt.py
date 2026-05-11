from pathlib import Path
from typing import Optional

import typer
from typing_extensions import Annotated

from datacontract.cli import OrderedCommandsWithMigrationHints, console, debug_option, enable_debug_logging
from datacontract.integration.dbt_sync import ModelResolution, check_dbt_on_path, generate_dbt_tests, run_tests
from datacontract.model.run import ResultEnum
from datacontract.output.test_results_writer import print_test_results_table, to_field

dbt_app = typer.Typer(cls=OrderedCommandsWithMigrationHints, no_args_is_help=True)


@dbt_app.command(
    name="sync",
    epilog="Example: datacontract dbt sync orders.odcs.yaml --project-dir ./warehouse",
)
def sync_command(
    contract: Annotated[
        Optional[str],
        typer.Argument(
            help="Path to the ODCS data contract. If omitted, searches for a single `*.odcs.yaml` in the current directory and its subdirectories.",
        ),
    ] = None,
    project_dir: Annotated[
        Optional[Path],
        typer.Option(
            help="Path to the dbt project root (must contain `dbt_project.yml`). Defaults to the current directory."
        ),
    ] = None,
    schema_name: Annotated[
        str,
        typer.Option(help="Which ODCS schema object to sync, by name."),
    ] = "all",
    model_resolution: Annotated[
        ModelResolution,
        typer.Option(help="How to map an ODCS schema to a dbt model name."),
    ] = ModelResolution.name,
    target: Annotated[Optional[str], typer.Option(help="Forwarded to `dbt test --target`.")] = None,
    profiles_dir: Annotated[
        Optional[Path],
        typer.Option(help="Forwarded to `dbt test --profiles-dir`."),
    ] = None,
    skip_tests: Annotated[
        bool,
        typer.Option("--skip-tests/--run-tests", help="Generate tests but skip running `dbt test`."),
    ] = False,
    debug: debug_option = None,
):
    """
    Generate dbt tests from an ODCS contract and run them.

    Wipes `<project>/models/datacontract_cli/` and `<project>/tests/datacontract_cli/`,
    regenerates them from the contract, then runs `dbt test`.
    """
    enable_debug_logging(debug)

    if not skip_tests:
        check_dbt_on_path()

    gen = generate_dbt_tests(
        contract=contract,
        project_dir=project_dir,
        schema_name=schema_name,
        model_resolution=model_resolution,
        console=console,
    )

    line = f"Wrote {len(gen.written_yaml)} YAML file(s) under models/datacontract_cli/"
    if gen.written_sql:
        line += f" and {len(gen.written_sql)} SQL file(s) under tests/datacontract_cli/"
    line += "."
    console.print(line)

    if skip_tests:
        return

    run = run_tests(gen, target=target, profiles_dir=profiles_dir)
    if not run.checks:
        console.print("[yellow]No test results parsed.[/yellow]")
        return

    print_test_results_table(run, console)
    total = len(run.checks)
    took = (run.timestampEnd - run.timestampStart).total_seconds()
    if run.result == ResultEnum.passed:
        console.print(f"🟢 dbt tests passed. Ran {total} tests. Took {took} seconds.")
        return
    if run.result == ResultEnum.warning:
        console.print("🟠 dbt tests have warnings:")
    else:
        console.print("🔴 dbt tests failed, found the following errors:")
    i = 1
    for check in run.checks:
        if check.result not in (None, ResultEnum.passed):
            field = to_field(run, check)
            prefix = f"{field} " if field else ""
            console.print(f"{i}) {prefix}{check.name}: {check.reason}")
            i += 1
    if run.result in (ResultEnum.failed, ResultEnum.error):
        raise typer.Exit(code=1)
