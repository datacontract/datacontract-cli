import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Set, Tuple

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
    _resolve_contract_paths,
    check_dbt_on_path,
    generate_dbt_tests,
    parse_dbt_test_run,
    resolve_model_names,
    run_dbt_test,
)
from datacontract.integration.entropy_data import publish_test_results_to_entropy_data
from datacontract.lint.resolve import resolve_data_contract
from datacontract.model.run import ResultEnum, Run
from datacontract.output.test_results_writer import print_test_results_table, to_field

dbt_app = typer.Typer(cls=OrderedCommandsWithMigrationHints, no_args_is_help=True)

_RESULT_EMOJI = {
    ResultEnum.passed: "🟢",
    ResultEnum.warning: "🟠",
    ResultEnum.failed: "🔴",
    ResultEnum.error: "🔴",
}


@dataclass
class _ContractCtx:
    """One contract resolved for a `dbt test` run (shared across sync's run path and `dbt test`)."""

    contract_path: Path
    odcs: object
    model_names: List[str]  # effective dbt model names — drive selection and result attribution
    generation_run: Optional[Run]  # set on sync's --run-tests path, None on `dbt test`


def _candidate_models(odcs) -> List[str]:
    """Model names a contract may own on disk — schema name and physicalName, strategy-agnostic.

    `dbt test` doesn't know which `--model-resolution` `dbt sync` used, so it matches on both.
    """
    names: List[str] = []
    for s in odcs.schema_ or []:
        if s.name:
            names.append(s.name)
        if getattr(s, "physicalName", None):
            names.append(s.physicalName)
    return names


def _check_no_overlap(contracts: List[Tuple[Path, List[str]]]) -> None:
    """Hard-error if any dbt model is claimed by more than one contract (write nothing first)."""
    owners: dict[str, List[Path]] = {}
    for path, model_names in contracts:
        for model in {m.lower() for m in model_names}:
            owners.setdefault(model, []).append(path)
    conflicts = {model: paths for model, paths in owners.items() if len(paths) > 1}
    if conflicts:
        lines = "\n".join(f"  - {model}: {', '.join(str(p) for p in paths)}" for model, paths in conflicts.items())
        console.print(
            f"[red]The same dbt model is claimed by multiple contracts:\n{lines}\n"
            "Select a single contract so each model has one owner.[/red]"
        )
        raise typer.Exit(code=1)


def _validate_server_declared(odcs, server: Optional[str]) -> None:
    """Reject a `--server` that the contract doesn't declare (when it declares any)."""
    if server is not None and odcs.servers:
        known = [s.server for s in odcs.servers if s.server]
        if server not in known:
            console.print(
                f"[red]--server {server!r} is not declared in the contract. Available: {', '.join(known) or '(none)'}[/red]"
            )
            raise typer.Exit(code=1)


def _resolve_run_server(odcs, server: Optional[str], target: Optional[str]) -> Optional[str]:
    if server is not None:
        return server
    if odcs.servers and len(odcs.servers) == 1:
        return odcs.servers[0].server
    return target


def _maybe_publish(run: Run, odcs, publish: Optional[str], ssl_verification: bool) -> bool:
    """Publish the run if requested; return True if a publish was attempted and failed."""
    if publish is None:
        return False
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
        return False
    return not publish_test_results_to_entropy_data(run, publish, ssl_verification)


def _report_run(run: Run, *, run_only: bool, publish_failed: bool, multi: bool, ctx: _ContractCtx) -> bool:
    """Print one contract's results; return True if it should fail the invocation."""
    if multi:
        console.print(f"\n[bold]Contract {run.dataContractId}@{run.dataContractVersion}[/bold] — {ctx.contract_path}")
    if not run.checks:
        if run_only:
            console.print(
                "[yellow]No managed tests found. Run `datacontract dbt sync` first to "
                "generate tests from your contract.[/yellow]"
            )
        else:
            console.print("[yellow]No test results parsed.[/yellow]")
        return publish_failed

    print_test_results_table(run, console)
    total = len(run.checks)
    took = (run.timestampEnd - run.timestampStart).total_seconds()
    if run.result == ResultEnum.passed:
        console.print(f"🟢 dbt tests passed. Ran {total} tests. Took {took} seconds.")
        return publish_failed
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
    return run.result in (ResultEnum.failed, ResultEnum.error) or publish_failed


def _print_footer(rows: List[Tuple[str, str, str]]) -> None:
    """Render the per-contract status block + tally (only shown when >1 contract was requested)."""
    console.print("\n[bold]Contract results:[/bold]")
    for emoji, label, status in rows:
        console.print(f"  {emoji} {label} — {status}")
    tally = {}
    for _, _, status in rows:
        tally[status] = tally.get(status, 0) + 1
    summary = " · ".join(f"{n} {status}" for status, n in tally.items())
    console.print(f"Tested {len(rows)} contract(s): {summary}.")


def _run_and_report(
    ctxs: List[_ContractCtx],
    project_dir: Path,
    *,
    target: Optional[str],
    profiles_dir: Optional[Path],
    publish: Optional[str],
    server: Optional[str],
    ssl_verification: bool,
    error_rows: List[Tuple[Path, str]],
    multi: bool,
) -> bool:
    """Run `dbt test` once (scoped to all requested contracts' models), then report per contract.

    Returns True if the invocation should exit non-zero.
    """
    union_models = sorted({m for c in ctxs for m in c.model_names})
    if union_models:
        completed = run_dbt_test(project_dir, target=target, profiles_dir=profiles_dir, models=union_models)
    else:
        completed = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")

    any_failed = bool(error_rows)
    footer: List[Tuple[str, str, str]] = []
    for c in ctxs:
        model_filter: Set[str] = {m.lower() for m in c.model_names}
        run = parse_dbt_test_run(
            project_dir, c.odcs, completed, model_filter=model_filter, generation_run=c.generation_run
        )
        run.server = _resolve_run_server(c.odcs, server, target)
        publish_failed = _maybe_publish(run, c.odcs, publish, ssl_verification)
        failed = _report_run(
            run, run_only=(c.generation_run is None), publish_failed=publish_failed, multi=multi, ctx=c
        )
        any_failed = any_failed or failed
        label = f"{run.dataContractId}@{run.dataContractVersion}"
        if not run.checks:
            footer.append(("⚪", label, "no tests"))
        else:
            footer.append((_RESULT_EMOJI.get(run.result, "🔴"), label, run.result.value))

    for path, msg in error_rows:
        console.print(f"[red]🔴 {path}: {msg}[/red]")
        footer.append(("🔴", str(path), "error"))

    if multi:
        _print_footer(footer)
    return any_failed


@dbt_app.command(
    name="sync",
    epilog="Example: datacontract dbt sync orders.odcs.yaml --project-dir ./warehouse",
)
def sync_command(
    contract: Annotated[
        Optional[List[str]],
        typer.Argument(
            help="Path(s) or glob(s) of ODCS contracts to sync. If omitted, syncs every `*.odcs.yaml` "
            "under --project-dir (default: current directory) and its subdirectories.",
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
    Generate dbt tests and model metadata from one or more ODCS contracts.

    Modifies the existing dbt model YAML in place (preserving comments and formatting), and creates new model YAML files
    or singular SQL tests if needed. Generate-only by default; pass `--run-tests` (or `--publish`/`--server`) to also run
    `dbt test`. With multiple contracts, each is synced independently. Use `datacontract dbt test` to run them later.
    """
    enable_debug_logging(debug)
    validate_publish_url(publish)

    # --publish / --server have no meaning without a run, so they imply --run-tests.
    if publish is not None or server is not None:
        run_tests_flag = True

    project_dir = (project_dir or Path.cwd()).resolve()
    _ensure_dbt_project(project_dir)
    paths = _resolve_contract_paths(contract or [], project_dir)
    multi = len(paths) > 1

    # Load + resolve models for the overlap pre-flight, before any contract writes to disk.
    loaded: List[Tuple[Path, object, List[str]]] = []
    error_rows: List[Tuple[Path, str]] = []
    for path in paths:
        try:
            odcs = resolve_data_contract(str(path))
            model_names = list(resolve_model_names(odcs, model_resolution, schema_name).values())
            loaded.append((path, odcs, model_names))
        except Exception as e:
            if not multi:
                raise
            error_rows.append((path, str(e)))
    _check_no_overlap([(p, mn) for p, _, mn in loaded])
    for _, odcs, _ in loaded:
        _validate_server_declared(odcs, server)

    ctxs: List[_ContractCtx] = []
    for path, _, _ in loaded:
        try:
            gen = generate_dbt_tests(
                contract=str(path),
                project_dir=project_dir,
                schema_name=schema_name,
                model_resolution=model_resolution,
                prune=prune,
            )
        except Exception as e:
            if not multi:
                raise
            error_rows.append((path, str(e)))
            continue
        if not contract:
            console.print(f"Resolved contract {gen.contract_path}")
        for schema in gen.skipped_schemas:
            console.print(f"[yellow]Skipped schema {schema!r}: no matching dbt model found.[/yellow]")
        prefix = f"{gen.contract_path.name}: " if multi else ""
        line = f"{prefix}Synced {len(gen.resolved_models)} model(s): updated {len(gen.written_yaml)} YAML file(s)"
        if gen.written_sql:
            line += f", wrote {len(gen.written_sql)} singular SQL test(s) under {gen.written_sql[0].parent}"
        if gen.deleted_files:
            line += f", removed {len(gen.deleted_files)} YAML file(s)"
        console.print(line + ".")
        ctxs.append(_ContractCtx(gen.contract_path, gen.odcs, gen.resolved_models, gen.generation_run))

    if not run_tests_flag:
        console.print("Next: run `datacontract dbt test` to execute the generated tests.")
        for path, msg in error_rows:
            console.print(f"[red]🔴 {path}: {msg}[/red]")
        if error_rows:
            raise typer.Exit(code=1)
        return

    check_dbt_on_path()
    failed = _run_and_report(
        ctxs,
        project_dir,
        target=target,
        profiles_dir=profiles_dir,
        publish=publish,
        server=server,
        ssl_verification=ssl_verification,
        error_rows=error_rows,
        multi=multi,
    )
    if failed:
        raise typer.Exit(code=1)


@dbt_app.command(
    name="test",
    epilog="Example: datacontract dbt test orders.odcs.yaml --project-dir ./warehouse",
)
def test_command(
    contract: Annotated[
        Optional[List[str]],
        typer.Argument(
            help="Path(s) or glob(s) of ODCS contracts to test. If omitted, tests every `*.odcs.yaml` "
            "under --project-dir (default: current directory) and its subdirectories.",
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

    Runs `dbt test` scoped to the requested contracts' managed tests, reports the results, and optionally publishes
    them. Never modifies project files — run `datacontract dbt sync` first to (re)generate the tests. With multiple
    contracts, each contract's results are reported (and published) separately.
    """
    enable_debug_logging(debug)
    validate_publish_url(publish)
    check_dbt_on_path()

    project_dir = (project_dir or Path.cwd()).resolve()
    _ensure_dbt_project(project_dir)
    paths = _resolve_contract_paths(contract or [], project_dir)
    multi = len(paths) > 1

    ctxs: List[_ContractCtx] = []
    error_rows: List[Tuple[Path, str]] = []
    for path in paths:
        try:
            odcs = resolve_data_contract(str(path))
        except Exception as e:
            if not multi:
                raise
            error_rows.append((path, str(e)))
            continue
        if not contract:
            console.print(f"Resolved contract {path}")
        ctxs.append(_ContractCtx(path, odcs, _candidate_models(odcs), None))

    _check_no_overlap([(c.contract_path, c.model_names) for c in ctxs])
    for c in ctxs:
        _validate_server_declared(c.odcs, server)

    failed = _run_and_report(
        ctxs,
        project_dir,
        target=target,
        profiles_dir=profiles_dir,
        publish=publish,
        server=server,
        ssl_verification=ssl_verification,
        error_rows=error_rows,
        multi=multi,
    )
    if failed:
        raise typer.Exit(code=1)
