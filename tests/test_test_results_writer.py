import typer
from rich.console import Console
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.model.run import Check, ResultEnum, Run
from datacontract.output.test_results_writer import write_test_result

runner = CliRunner()

NESTED = "Checks on nested properties are not supported on postgres servers."


def _printed(checks) -> str:
    run = Run.create_run()
    run.checks = checks
    run.finish()
    console = Console(record=True, width=300)
    try:
        write_test_result(run, console, None, None)
    except typer.Exit:
        pass
    return console.export_text()


def test_checks_sharing_a_reason_are_listed_once_below_the_table():
    printed = _printed(
        [
            Check(type="field_required", name="Check a", field="user.email", result=ResultEnum.warning, reason=NESTED),
            Check(type="field_regex", name="Check b", field="user.email", result=ResultEnum.warning, reason=NESTED),
            Check(type="field_required", name="Check c", field="items[].sku", result=ResultEnum.warning, reason=NESTED),
            Check(type="field_type", name="Check d", field="amount", result=ResultEnum.failed, reason="was 1"),
        ]
    )

    summary = printed.split("found the following errors:")[1]
    assert f"1) 3 checks on user.email, items[].sku: {NESTED}" in summary
    assert "2) amount Check d: was 1" in summary
    table = printed.split("found the following errors:")[0]
    assert all(f"Check {name}" in table for name in "abcd")


def test_a_reason_of_its_own_keeps_its_check_line():
    printed = _printed(
        [Check(type="field_type", name="Check d", field="amount", result=ResultEnum.warning, reason="was 1")]
    )

    assert "1) amount Check d: was 1" in printed


def test_brackets_in_a_check_name_are_printed_in_the_table():
    printed = _printed([Check(type="field_quality_custom", name="in_list(x=[a, b])", result=ResultEnum.passed)])

    assert "in_list(x=[a, b])" in printed


def test_a_selection_that_matches_nothing_is_not_a_failure():
    result = runner.invoke(app, ["test", "--tag", "nightly", "./fixtures/quality-id/datacontract.yaml"])
    assert result.exit_code == 0
    assert "⚪ No checks were executed. Took" in result.stdout


def test_a_contract_without_schema_is_not_a_failure(tmp_path):
    contract = tmp_path / "datacontract.yaml"
    contract.write_text("apiVersion: v3.1.0\nkind: DataContract\nid: no-schema\nversion: 1.0.0\nstatus: draft\n")
    result = runner.invoke(app, ["test", "--logs", str(contract)])
    assert result.exit_code == 0
    assert "⚪ No checks were executed. Took" in result.stdout
    assert "The data contract declares no schema" in result.stdout


def test_a_run_that_skipped_every_check_says_so():
    result = runner.invoke(
        app, ["test", "--checks", "quality", "--metadata-only", "./fixtures/quality-id/datacontract.yaml"]
    )
    assert result.exit_code == 0
    assert "All checks were skipped" in result.stdout
