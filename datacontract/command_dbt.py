from pathlib import Path
from typing import Optional

import typer
from typing_extensions import Annotated

from datacontract.cli import (
    OrderedCommandsWithMigrationHints,
    console,
    debug_option,
    enable_debug_logging,
    validate_publish_url,
)
from datacontract.integration.dbt_sync import (
    ModelResolution,
    _ensure_dbt_project,
    _resolve_contract_path,
    check_dbt_on_path,
    generate_dbt_tests,
    run_tests,
)
from datacontract.integration.entropy_data import publish_test_results_to_entropy_data
from datacontract.lint.resolve import resolve_data_contract
from datacontract.model.run import ResultEnum, Run
from datacontract.output.test_results_writer import print_test_results_table, to_field

dbt_app = typer.Typer(cls=OrderedCommandsWithMigrationHints, no_args_is_help=True)


def _validate_server_declared(odcs, server: Optional[str]) -> None:
    """Reject a `--server` that the contract doesn't declare (when it declares any)."""
    if server is not None and odcs.servers:
        known = [s.server for s in odcs.servers if s.server]
        if server not in known:
            console.print(
                f"[red]--server {server!r} is not declared in the contract. Available: {', '.join(known) or '(none)'}[/red]"
            )
            raise typer.Exit(code=1)


def _run_and_report(
    odcs,
    project_dir: Path,
    *,
    target: Optional[str],
    profiles_dir: Optional[Path],
    publish: Optional[str],
    server: Optional[str],
    ssl_verification: bool,
    generation_run: Optional[Run] = None,
) -> None:
    """Run `dbt test`, resolve the run's server, optionally publish, print results, exit non-zero on failure.

    Shared by `dbt sync --run-tests` (passes `generation_run`) and `dbt test` (passes None) so both
    run/parse/publish/report identically.
    """
    run = run_tests(odcs, project_dir, target=target, profiles_dir=profiles_dir, generation_run=generation_run)
    if server is not None:
        run.server = server
    elif odcs.servers and len(odcs.servers) == 1:
        run.server = odcs.servers[0].server
    else:
        run.server = target

    publish_failed = False
    if publish is not None:
        if run.server is None:
            if not odcs.servers:
                console.print(
                    "[yellow]Skipping publish: the contract declares no servers. "
                    "Add a `servers:` block or pass --server to identify the run.[/yellow]"
                )
            else:
                known = ", ".join(s.server for s in odcs.servers if s.server) or "(none)"
                console.print(
                    f"[yellow]Skipping publish: the contract declares multiple servers ({known}). "
                    f"Pass --server to identify the run.[/yellow]"
                )
        else:
            publish_failed = not publish_test_results_to_entropy_data(run, publish, ssl_verification)

    if not run.checks:
        if generation_run is None:
            console.print(
                "[yellow]No managed tests found. Run `datacontract dbt sync` first to "
                "generate tests from your contract.[/yellow]"
            )
        else:
            console.print("[yellow]No test results parsed.[/yellow]")
        if publish_failed:
            raise typer.Exit(code=1)
        return

    print_test_results_table(run, console)
    total = len(run.checks)
    took = (run.timestampEnd - run.timestampStart).total_seconds()
    if run.result == ResultEnum.passed:
        console.print(f"🟢 dbt tests passed. Ran {total} tests. Took {took} seconds.")
        if publish_failed:
            raise typer.Exit(code=1)
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
    if run.result in (ResultEnum.failed, ResultEnum.error) or publish_failed:
        raise typer.Exit(code=1)


@dbt_app.command(
    name="sync",
    epilog="Example: datacontract dbt sync orders.odcs.yaml --project-dir ./warehouse",
)
def sync_command(
    contract: Annotated[
        Optional[str],
        typer.Argument(
            help="Path to the ODCS data contract. If omitted, searches for a single `*.odcs.yaml` in --project-dir (default: current directory) and its subdirectories.",
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
    prune: Annotated[
        bool,
        typer.Option(help="Remove model columns and tags that are not declared in the contract."),
    ] = False,
    run_tests_flag: Annotated[
        bool,
        typer.Option(
            "--run-tests/--skip-tests",
            help="Run `dbt test` on the generated tests after syncing. Default: skip (generate only). Implied by --publish/--server.",
        ),
    ] = False,
    publish: Annotated[Optional[str], typer.Option(help="The url to publish the results after the test.")] = None,
    server: Annotated[
        Optional[str],
        typer.Option(
            help="ODCS server name for published test results. Auto-selected if the contract contains only one server. Otherwise defaults to --target.",
        ),
    ] = None,
    ssl_verification: Annotated[bool, typer.Option(help="SSL verification when publishing test results.")] = True,
    debug: debug_option = None,
):
    """
    Generate dbt tests and model metadata from an ODCS contract.

    Modifies the existing dbt model YAML in place (preserving comments and formatting), and creates new model YAML files
    or singular SQL tests if needed. Generate-only by default; pass `--run-tests` (or `--publish`/`--server`) to also run
    `dbt test --select config.meta.datacontract_cli.include_in_tests:true`. Use `datacontract dbt test` to run them later.
    """
    enable_debug_logging(debug)
    validate_publish_url(publish)

    # --publish / --server have no meaning without a run, so they imply --run-tests.
    if publish is not None or server is not None:
        run_tests_flag = True

    gen = generate_dbt_tests(
        contract=contract,
        project_dir=project_dir,
        schema_name=schema_name,
        model_resolution=model_resolution,
        prune=prune,
    )
    if contract is None:
        console.print(f"Resolved contract {gen.contract_path}")

    for schema in gen.skipped_schemas:
        console.print(f"[yellow]Skipped schema {schema!r}: no matching dbt model found.[/yellow]")

    _validate_server_declared(gen.odcs, server)

    line = f"Synced {len(gen.resolved_models)} model(s): updated {len(gen.written_yaml)} YAML file(s)"
    if gen.written_sql:
        sql_dir = gen.written_sql[0].parent
        line += f", wrote {len(gen.written_sql)} singular SQL test(s) under {sql_dir}"
    if gen.deleted_files:
        line += f", removed {len(gen.deleted_files)} YAML file(s)"
    line += "."
    console.print(line)

    if not run_tests_flag:
        console.print("Next: run `datacontract dbt test` to execute the generated tests.")
        return

    check_dbt_on_path()
    _run_and_report(
        gen.odcs,
        gen.project_dir,
        target=target,
        profiles_dir=profiles_dir,
        publish=publish,
        server=server,
        ssl_verification=ssl_verification,
        generation_run=gen.generation_run,
    )


@dbt_app.command(
    name="test",
    epilog="Example: datacontract dbt test orders.odcs.yaml --project-dir ./warehouse",
)
def test_command(
    contract: Annotated[
        Optional[str],
        typer.Argument(
            help="Path to the ODCS data contract. If omitted, searches for a single `*.odcs.yaml` in --project-dir (default: current directory) and its subdirectories.",
        ),
    ] = None,
    project_dir: Annotated[
        Optional[Path],
        typer.Option(
            help="Path to the dbt project root (must contain `dbt_project.yml`). Defaults to the current directory."
        ),
    ] = None,
    target: Annotated[Optional[str], typer.Option(help="Forwarded to `dbt test --target`.")] = None,
    profiles_dir: Annotated[
        Optional[Path],
        typer.Option(help="Forwarded to `dbt test --profiles-dir`."),
    ] = None,
    publish: Annotated[Optional[str], typer.Option(help="The url to publish the results after the test.")] = None,
    server: Annotated[
        Optional[str],
        typer.Option(
            help="ODCS server name for published test results. Auto-selected if the contract contains only one server. Otherwise defaults to --target.",
        ),
    ] = None,
    ssl_verification: Annotated[bool, typer.Option(help="SSL verification when publishing test results.")] = True,
    debug: debug_option = None,
):
    """
    Run the contract-managed dbt tests that `datacontract dbt sync` generated.

    Runs `dbt test --select config.meta.datacontract_cli.include_in_tests:true`, reports the results, and optionally
    publishes them. Never modifies project files — run `datacontract dbt sync` first to (re)generate the tests.
    """
    enable_debug_logging(debug)
    validate_publish_url(publish)
    check_dbt_on_path()

    project_dir = (project_dir or Path.cwd()).resolve()
    _ensure_dbt_project(project_dir)
    contract_path = _resolve_contract_path(contract, project_dir)
    odcs = resolve_data_contract(str(contract_path))
    if contract is None:
        console.print(f"Resolved contract {contract_path}")

    _validate_server_declared(odcs, server)

    _run_and_report(
        odcs,
        project_dir,
        target=target,
        profiles_dir=profiles_dir,
        publish=publish,
        server=server,
        ssl_verification=ssl_verification,
        generation_run=None,
    )
