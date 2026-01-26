from pathlib import Path
from typing import Optional

import typer
from open_data_contract_standard.model import OpenDataContractStandard
from rich import box
from rich.console import Console
from rich.table import Table

from datacontract.model.run import Run
from datacontract.output.junit_test_results import write_junit_test_results
from datacontract.output.output_format import OutputFormat


def write_test_result(
    run: Run,
    console: Console,
    output_format: OutputFormat,
    output_path: Path,
    data_contract: Optional[OpenDataContractStandard] = None,
):
    if output_format == OutputFormat.junit:
        write_junit_test_results(run, console, output_path)

    if run.server and data_contract and data_contract.servers:
        server = next((s for s in data_contract.servers if s.server == run.server), None)
        if server:
            details = []
            if server.type:
                details.append(f"type={server.type}")
            if server.format:
                details.append(f"format={server.format}")
            if server.host:
                details.append(f"host={server.host}")
            if server.port:
                details.append(f"port={server.port}")
            if server.database:
                details.append(f"database={server.database}")
            if server.schema_:
                details.append(f"schema={server.schema_}")
            if server.catalog:
                details.append(f"catalog={server.catalog}")
            if server.dataset:
                details.append(f"dataset={server.dataset}")
            if server.project:
                details.append(f"project={server.project}")
            if server.account:
                details.append(f"account={server.account}")
            if server.location:
                details.append(f"location={server.location}")
            if server.path:
                details.append(f"path={server.path}")
            details_str = ", ".join(details) if details else ""
            if details_str:
                console.print(f"Server: {run.server} ({details_str})")

    _print_table(run, console)
    if run.result == "passed":
        console.print(
            f"🟢 data contract is valid. Run {len(run.checks)} checks. Took {(run.timestampEnd - run.timestampStart).total_seconds()} seconds."
        )
    elif run.result == "warning":
        console.print("🟠 data contract has warnings. Found the following warnings:")
        i = 1
        for check in run.checks:
            if check.result != "passed":
                field = to_field(run, check)
                if field:
                    field = field + " "
                else:
                    field = ""
                console.print(f"{i}) {field}{check.name}: {check.reason}")
                i += 1
    else:
        console.print("🔴 data contract is invalid, found the following errors:")
        i = 1
        for check in run.checks:
            if check.result != "passed":
                field = to_field(run, check)
                if field:
                    field = field + " "
                else:
                    field = ""
                console.print(f"{i}) {field}{check.name}: {check.reason}")
                i += 1
        raise typer.Exit(code=1)


def _print_table(run, console):
    table = Table(box=box.ROUNDED)
    table.add_column("Result", no_wrap=True)
    table.add_column("Check", max_width=100)
    table.add_column("Field", max_width=32)
    table.add_column("Details", max_width=50)
    for check in sorted(run.checks, key=lambda c: (c.result or "", c.model or "", c.field or "")):
        table.add_row(with_markup(check.result), check.name, to_field(run, check), check.reason)
    console.print(table)


def to_field(run, check):
    models = [c.model for c in run.checks]
    if len(set(models)) > 1:
        if check.field is None:
            return check.model
        return check.model + "." + check.field
    else:
        return check.field


def with_markup(result):
    if result == "passed":
        return "[green]passed[/green]"
    if result == "warning":
        return "[yellow]warning[/yellow]"
    if result == "failed":
        return "[red]failed[/red]"
    if result == "error":
        return "[red]error[/red]"
    return result
