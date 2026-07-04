import subprocess
from dataclasses import dataclass
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
    _resolve_contract_paths,
    check_dbt_on_path,
    generate_dbt_tests,
    parse_dbt_test_run,
    parse_filename_version,
    resolve_model_names,
    resolve_versioned_target,
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
    model_names: list[str]  # effective dbt model names — drive selection and result attribution
    generation_run: Optional[Run]  # set on sync's --run-tests path, None on `dbt test`
    dbt_version: Optional[str] = None  # filename-derived dbt model version, when this contract is versioned


def _candidate_models(odcs) -> list[str]:
    """Model names a contract may own on disk — schema name and physicalName, strategy-agnostic.

    `dbt test` doesn't know which `--model-resolution` `dbt sync` used, so it matches on both.
    """
    names: list[str] = []
    for s in odcs.schema_ or []:
        if s.name:
            names.append(s.name)
        if getattr(s, "physicalName", None):
            names.append(s.physicalName)
    return names


@dataclass
class _Owner:
    path: Path
    contract_id: object
    contract_version: object
    dbt_version: Optional[str]  # filename-derived version, None if the contract can't map to one


def _check_model_ownership(owners_by_model: dict) -> None:
    """Hard-error unless every model shared by multiple contracts is a clean version group.

    A shared model is allowed only when its owners are versions of the *same* contract: one
    `odcs.id`, distinct `version`s, and each with a filename `v<N>` that maps to a dbt model version.
    """
    errors: list[str] = []
    for model, owners in owners_by_model.items():
        if len(owners) < 2:
            continue
        ids = {o.contract_id for o in owners}
        versions = [o.contract_version for o in owners]
        if len(ids) > 1:
            listed = ", ".join(f"{o.path.name} ({o.contract_id})" for o in owners)
            errors.append(f"  - `{model}` is claimed by different contracts: {listed}")
        elif len(set(versions)) != len(versions):
            errors.append(f"  - `{model}`: two contracts share id `{next(iter(ids))}` and version `{versions[0]}`")
        elif any(o.dbt_version is None for o in owners):
            listed = ", ".join(o.path.name for o in owners if o.dbt_version is None)
            errors.append(
                f"  - `{model}`: same-id versions can't map to dbt model versions "
                f"(need a `v<N>` filename and a `{model}_v<N>.sql`): {listed}"
            )
    if errors:
        console.print("[red]Cannot sync — overlapping dbt models:\n" + "\n".join(errors) + "[/red]")
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


def _report_run(run: Run, *, run_only: bool, publish_failed: bool, ctx: _ContractCtx) -> bool:
    """Print one contract's results; return True if it should fail the invocation."""
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


def _rel(path: Path, project_dir: Path) -> str:
    try:
        return str(path.relative_to(project_dir))
    except ValueError:
        return str(path)


def _count(n: int, noun: str) -> str:
    return f"{n} {noun}" + ("" if n == 1 else "s")


# List filenames individually up to this many; beyond it, truncate with "... and N more".
_MAX_LISTED_FILES = 5


def _print_sync_summary(gen, project_dir: Path, *, debug: bool = False) -> None:
    """Print the per-contract sync summary, naming the touched files."""
    prefix = f"{gen.contract_path.name}: "
    line = f"{prefix}Synced {_count(len(gen.resolved_models), 'model')}: updated {_count(len(gen.written_yaml), 'YAML file')}"
    if gen.written_sql:
        line += f", wrote {_count(len(gen.written_sql), 'singular SQL test')}"
    if gen.deleted_files:
        line += f", removed {_count(len(gen.deleted_files), 'YAML file')}"
    console.print(line + ".")

    entries = (
        [f"~ {_rel(p, project_dir)}" for p in gen.written_yaml]
        + [f"+ {_rel(p, project_dir)}" for p in gen.written_sql]
        + [f"- {_rel(p, project_dir)}" for p in gen.deleted_files]
    )
    shown = entries if debug else entries[:_MAX_LISTED_FILES]
    for entry in shown:
        console.print(f"  {entry}")
    if len(entries) > len(shown):
        console.print(f"  ... and {len(entries) - len(shown)} more [dim](pass --debug to show all)[/dim]")


def _warn_prunable(gen, project_dir: Path) -> None:
    """Warn that the project has contract-absent columns/tags `--prune` would remove (it wasn't passed)."""
    if not gen.prunable:
        return
    prefix = f"{gen.contract_path.name}: "
    shown = gen.prunable[:_MAX_LISTED_FILES]
    console.print(
        f"[yellow]{prefix}{_count(len(gen.prunable), 'item')} in the project "
        f"{'is' if len(gen.prunable) == 1 else 'are'} not declared in the contract; "
        "pass --prune to remove:[/yellow]"
    )
    for item in shown:
        console.print(f"[yellow]  - {item}[/yellow]")
    if len(gen.prunable) > len(shown):
        console.print(f"[yellow]  ... and {len(gen.prunable) - len(shown)} more[/yellow]")


def _run_and_report(
    ctxs: list[_ContractCtx],
    project_dir: Path,
    *,
    target: Optional[str],
    profiles_dir: Optional[Path],
    publish: Optional[str],
    server: Optional[str],
    ssl_verification: bool,
    error_rows: list[tuple[Path, str]],
    multiple_contracts: bool,
) -> bool:
    """Run `dbt test` once (scoped to all requested contracts' models), then report per contract.

    Returns True if the invocation should exit non-zero.
    """
    model_versions = sorted(
        {(m, c.dbt_version, str(c.odcs.version or "no_version")) for c in ctxs for m in c.model_names},
        key=lambda t: (t[0], t[1] or "", t[2]),
    )
    if model_versions:
        completed = run_dbt_test(project_dir, target=target, profiles_dir=profiles_dir, model_versions=model_versions)
    else:
        completed = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")

    any_failed = bool(error_rows)
    footer: list[tuple[str, str, str]] = []
    for c in ctxs:
        model_filter: set[str] = {m.lower() for m in c.model_names}
        run = parse_dbt_test_run(
            project_dir, c.odcs, completed, model_filter=model_filter, generation_run=c.generation_run
        )
        if server is not None:
            run.server = server
        elif c.odcs.servers and len(c.odcs.servers) == 1:
            run.server = c.odcs.servers[0].server
        else:
            run.server = target
        publish_failed = _maybe_publish(run, c.odcs, publish, ssl_verification)
        failed = _report_run(
            run,
            run_only=(c.generation_run is None),
            publish_failed=publish_failed,
            ctx=c,
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

    if multiple_contracts:
        # Render the per-contract status block + tally.
        console.print("\n[bold]Contract results:[/bold]")
        for emoji, label, status in footer:
            console.print(f"  {emoji} {label} — {status}")
        tally = {}
        for _, _, status in footer:
            tally[status] = tally.get(status, 0) + 1
        summary = " · ".join(f"{n} {status}" for status, n in tally.items())
        console.print(f"Tested {len(footer)} contract(s): {summary}.")
    return any_failed


@dbt_app.command(
    name="sync",
    epilog="Example: datacontract dbt sync orders.odcs.yaml --project-dir ./warehouse",
)
def sync_command(
    contract: Annotated[
        Optional[list[str]],
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
            help="Run `dbt test` on the generated tests after syncing. Default: skip (generate only). Required by --publish/--server.",
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
    or singular SQL tests if needed. Use `datacontract dbt test` or pass --run-tests to run the generated tests.
    """
    enable_debug_logging(debug)
    validate_publish_url(publish)

    if (publish is not None or server is not None) and not run_tests_flag:
        console.print("[red]--publish/--server require --run-tests.[/red]")
        raise typer.Exit(code=1)

    project_dir = (project_dir or Path.cwd()).resolve()
    _ensure_dbt_project(project_dir)
    paths = _resolve_contract_paths(contract or [], project_dir)
    multiple_contracts = len(paths) > 1

    # Load + resolve models for the ownership pre-flight, before any contract writes to disk.
    loaded: list[tuple[Path, object, list[str], Optional[str]]] = []
    error_rows: list[tuple[Path, str]] = []
    owners_by_model: dict = {}
    for path in paths:
        try:
            odcs = resolve_data_contract(str(path))
            model_names = list(resolve_model_names(odcs, model_resolution, schema_name).values())
            dbt_version = resolve_versioned_target(project_dir, model_names, parse_filename_version(path))
            loaded.append((path, odcs, model_names, dbt_version))
            for model in {m.lower() for m in model_names}:
                owners_by_model.setdefault(model, []).append(
                    _Owner(path, odcs.id, odcs.version or "no_version", dbt_version)
                )
        except Exception as e:
            if not multiple_contracts:
                raise
            error_rows.append((path, str(e)))
    _check_model_ownership(owners_by_model)
    for _, odcs, _, _ in loaded:
        _validate_server_declared(odcs, server)

    ctxs: list[_ContractCtx] = []
    for path, odcs, _, dbt_version in loaded:
        try:
            gen = generate_dbt_tests(
                contract=str(path),
                project_dir=project_dir,
                schema_name=schema_name,
                model_resolution=model_resolution,
                prune=prune,
                model_version=dbt_version,
            )
        except Exception as e:
            if not multiple_contracts:
                raise
            error_rows.append((path, str(e)))
            continue
        if not contract and not multiple_contracts:
            console.print(f"Resolved contract {gen.contract_path}")
        for schema in gen.skipped_schemas:
            console.print(f"[yellow]Skipped schema {schema!r}: no matching dbt model found.[/yellow]")
        _print_sync_summary(gen, project_dir, debug=bool(debug))
        if not prune:
            _warn_prunable(gen, project_dir)
        ctxs.append(_ContractCtx(gen.contract_path, gen.odcs, gen.resolved_models, gen.generation_run, dbt_version))

    if not run_tests_flag:
        console.print("[dim]Run `datacontract dbt test` to execute the generated tests.[/dim]")
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
        multiple_contracts=multiple_contracts,
    )
    if failed:
        raise typer.Exit(code=1)


@dbt_app.command(
    name="test",
    epilog="Example: datacontract dbt test orders.odcs.yaml --project-dir ./warehouse",
)
def test_command(
    contract: Annotated[
        Optional[list[str]],
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

    Runs `dbt test` scoped to the specified data contract(s), reports the results, and optionally publishes
    them. Use `datacontract dbt sync` to create and update the tests first.
    """
    enable_debug_logging(debug)
    validate_publish_url(publish)
    check_dbt_on_path()

    project_dir = (project_dir or Path.cwd()).resolve()
    _ensure_dbt_project(project_dir)
    paths = _resolve_contract_paths(contract or [], project_dir)
    multiple_contracts = len(paths) > 1

    ctxs: list[_ContractCtx] = []
    error_rows: list[tuple[Path, str]] = []
    owners_by_model: dict = {}
    for path in paths:
        try:
            odcs = resolve_data_contract(str(path))
        except Exception as e:
            if not multiple_contracts:
                raise
            error_rows.append((path, str(e)))
            continue
        if not contract and not multiple_contracts:
            console.print(f"Resolved contract {path}")
        model_names = _candidate_models(odcs)
        dbt_version = resolve_versioned_target(project_dir, model_names, parse_filename_version(path))
        ctxs.append(_ContractCtx(path, odcs, model_names, None, dbt_version))
        for model in {m.lower() for m in model_names}:
            owners_by_model.setdefault(model, []).append(
                _Owner(path, odcs.id, odcs.version or "no_version", dbt_version)
            )

    _check_model_ownership(owners_by_model)
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
        multiple_contracts=multiple_contracts,
    )
    if failed:
        raise typer.Exit(code=1)
